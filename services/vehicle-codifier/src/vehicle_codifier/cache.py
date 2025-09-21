"""Vehicle catalog caching for optimal matching performance."""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple, Any
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from .config import get_settings
from .models import Candidate


class VehicleCatalogCache:
    """In-memory catalog cache with vector similarity search."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)

        # Cache data structures
        self._catalog_data: List[Dict] = []
        self._embeddings: Optional[np.ndarray] = None
        self._last_refresh: Optional[datetime] = None
        self._cache_lock = threading.RLock()
        self._is_loaded = False

        # Load cache on startup if enabled
        if self.settings.cache_enabled and self.settings.cache_preload_on_startup:
            self.refresh_cache()

    def refresh_cache(self) -> bool:
        """Refresh the in-memory cache from database."""
        try:
            start_time = time.time()
            print("🔄 Refreshing catalog cache from database...")

            with self._cache_lock:
                # Load catalog data with embeddings
                with Session(self.engine) as session:
                    result = session.execute(text("""
                        SELECT cvegs, marca, submarca, numver, ramo, cvemarc, cvesubm,
                               martip, cvesegm, modelo, descveh, idperdiod, sumabas, tipveh,
                               label, embedding
                        FROM amis_catalog
                        WHERE catalog_version = (
                            SELECT version FROM catalog_import WHERE status IN ('ACTIVE', 'LOADED') ORDER BY version DESC LIMIT 1
                        )
                        ORDER BY cvegs
                    """))

                    rows = result.fetchall()

                    if not rows:
                        print("⚠️ No catalog data found")
                        return False

                    # Store catalog metadata
                    self._catalog_data = []
                    embeddings_list = []

                    for row in rows:
                        # Always add catalog record regardless of embedding
                        catalog_record = {
                            'cvegs': row.cvegs,
                            'marca': row.marca,
                            'submarca': row.submarca,
                            'numver': row.numver,
                            'ramo': row.ramo,
                            'cvemarc': row.cvemarc,
                            'cvesubm': row.cvesubm,
                            'martip': row.martip,
                            'cvesegm': row.cvesegm,
                            'modelo': row.modelo,
                            'descveh': row.descveh,
                            'idperdiod': row.idperdiod,
                            'sumabas': row.sumabas,
                            'tipveh': row.tipveh,
                            'label': row.label
                        }
                        self._catalog_data.append(catalog_record)

                        # Only process embedding if it exists
                        if row.embedding is not None:
                            try:
                                # Convert string representation back to list
                                embedding_str = row.embedding.strip('[]')
                                embedding = [float(x.strip()) for x in embedding_str.split(',')]
                                embeddings_list.append(embedding)
                            except (ValueError, AttributeError) as e:
                                print(f"⚠️ Skipping embedding for row {row.cvegs}: {e}")
                                # Add placeholder for missing embedding to maintain index alignment
                                embeddings_list.append(None)
                        else:
                            # Add placeholder for missing embedding to maintain index alignment
                            embeddings_list.append(None)

                    # Process embeddings - filter out None values for numpy array
                    valid_embeddings = [emb for emb in embeddings_list if emb is not None]

                    if valid_embeddings:
                        self._embeddings = np.array(valid_embeddings, dtype=np.float32)
                        # Normalize embeddings for cosine similarity
                        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
                        self._embeddings = self._embeddings / norms

                        # Store embedding indices for mapping back to catalog records
                        self._embedding_indices = [i for i, emb in enumerate(embeddings_list) if emb is not None]

                        embedding_count = len(valid_embeddings)
                        total_count = len(self._catalog_data)
                        print(f"📊 Embeddings: {embedding_count}/{total_count} records ({embedding_count/total_count*100:.1f}%)")
                    else:
                        self._embeddings = None
                        self._embedding_indices = []
                        print("⚠️ No valid embeddings found, cache will use fuzzy matching only")

                    self._last_refresh = datetime.now()
                    self._is_loaded = True

                    load_time = (time.time() - start_time) * 1000
                    print(f"✅ Catalog cache loaded: {len(self._catalog_data)} records, {load_time:.2f}ms")

                    # Memory usage estimation
                    embeddings_size = self._embeddings.nbytes if self._embeddings is not None else 0
                    memory_mb = (embeddings_size + len(self._catalog_data) * 800) / 1024 / 1024
                    print(f"📊 Cache memory usage: ~{memory_mb:.1f}MB")

                    return True

        except Exception as e:
            print(f"❌ Cache refresh failed: {e}")
            self._is_loaded = False
            return False

    def should_refresh_cache(self) -> bool:
        """Check if cache should be refreshed based on age."""
        if not self._last_refresh:
            return True

        refresh_interval = timedelta(hours=self.settings.cache_refresh_interval_hours)
        return datetime.now() - self._last_refresh > refresh_interval

    def find_candidates_cached(
        self,
        query_embedding: List[float],
        query_label: str,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        brand_filter: Optional[str] = None
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Find candidates using in-memory cache with vector similarity."""

        if not self.is_cache_available():
            raise RuntimeError("Cache not available, use database fallback")

        with self._cache_lock:
            try:
                start_time = time.time()

                # Debug information collection
                debug_info = None
                candidates_after_year = []
                candidates_after_brand = []

                # Apply filters and collect candidates
                candidates = []
                candidates_filtered_by_brand = 0
                total_candidates_before_brand = 0
                year_filter_start_time = time.time()

                # Calculate similarities for records with embeddings if available
                similarities = {}
                if self._embeddings is not None and hasattr(self, '_embedding_indices'):
                    # Convert query embedding to numpy array and normalize
                    query_vec = np.array(query_embedding, dtype=np.float32)
                    query_vec = query_vec / np.linalg.norm(query_vec)

                    # Calculate cosine similarities using vectorized operations
                    embedding_similarities = np.dot(self._embeddings, query_vec)

                    # Map similarities back to catalog indices
                    for emb_idx, catalog_idx in enumerate(self._embedding_indices):
                        similarities[catalog_idx] = float(embedding_similarities[emb_idx])

                # Process all catalog records
                for i, catalog_record in enumerate(self._catalog_data):
                    # Apply year filter first
                    if year_min is not None or year_max is not None:
                        record_year = catalog_record['modelo']
                        if year_min is not None and record_year < year_min:
                            continue
                        if year_max is not None and record_year > year_max:
                            continue

                    # Get similarity score (0.0 if no embedding available)
                    similarity_score = similarities.get(i, 0.0)

                    # Store for debug if enabled
                    if self.settings.enable_debug_filtering:
                        candidates_after_year.append(Candidate(
                            cvegs=catalog_record['cvegs'],
                            marca=catalog_record['marca'],
                            submarca=catalog_record['submarca'],
                            modelo=catalog_record['modelo'],
                            descveh=catalog_record['descveh'],
                            label=catalog_record['label'],
                            similarity_score=similarity_score,
                            fuzzy_score=0.0,  # Will be calculated later
                            final_score=0.0   # Will be calculated later
                        ))

                    total_candidates_before_brand += 1

                    # Apply brand filter if provided and enabled
                    brand_filter_start_time = time.time() if total_candidates_before_brand == 1 else None
                    if (brand_filter and self.settings.enable_brand_filtering and
                        catalog_record['marca'].upper() != brand_filter.upper()):
                        candidates_filtered_by_brand += 1
                        continue

                    # Calculate fuzzy score for hybrid ranking
                    fuzzy_score = self._calculate_fuzzy_score(query_label, catalog_record['label'])

                    # Hybrid final score (70% embedding + 30% fuzzy)
                    final_score = (
                        self.settings.weight_embedding * similarity_score +
                        self.settings.weight_fuzzy * fuzzy_score
                    )

                    candidate = Candidate(
                        cvegs=catalog_record['cvegs'],
                        marca=catalog_record['marca'],
                        submarca=catalog_record['submarca'],
                        modelo=catalog_record['modelo'],
                        descveh=catalog_record['descveh'],
                        label=catalog_record['label'],
                        similarity_score=similarity_score,
                        fuzzy_score=fuzzy_score,
                        final_score=final_score
                    )
                    candidates.append(candidate)

                    # Store for debug after brand filtering if enabled
                    if self.settings.enable_debug_filtering:
                        candidates_after_brand.append(candidate)

                # Sort by final score and limit results
                candidates.sort(key=lambda x: x.final_score, reverse=True)
                final_candidates = candidates[:self.settings.max_candidates]

                search_time = (time.time() - start_time) * 1000
                embedding_status = f"(embeddings: {len(self._embedding_indices) if hasattr(self, '_embedding_indices') else 0}/{len(self._catalog_data)})" if self._embeddings is not None else "(fuzzy-only)"

                if brand_filter and candidates_filtered_by_brand > 0:
                    print(f"🚀 Cache search: {len(final_candidates)} candidates (filtered {candidates_filtered_by_brand}/{total_candidates_before_brand} by brand '{brand_filter}') {embedding_status}, {search_time:.2f}ms")
                else:
                    print(f"🚀 Cache search: {len(final_candidates)} candidates {embedding_status}, {search_time:.2f}ms")

                # Prepare debug information if enabled
                if self.settings.enable_debug_filtering:
                    year_filter_time = (time.time() - year_filter_start_time) * 1000 if year_filter_start_time else 0
                    brand_filter_time = (time.time() - brand_filter_start_time) * 1000 if brand_filter_start_time else 0

                    debug_info = {
                        "filtering_steps": {
                            "total_catalog_size": len(self._catalog_data),
                            "after_year_filter": len(candidates_after_year),
                            "after_brand_filter": len(candidates_after_brand),
                            "after_scoring_and_limit": len(final_candidates)
                        },
                        "applied_filters": {
                            "year_min": year_min,
                            "year_max": year_max,
                            "brand_filter": brand_filter,
                            "brand_filtering_enabled": brand_filter and self.settings.enable_brand_filtering
                        },
                        "embedding_info": {
                            "embeddings_available": self._embeddings is not None,
                            "embedding_count": len(self._embedding_indices) if hasattr(self, '_embedding_indices') else 0,
                            "total_records": len(self._catalog_data)
                        },
                        "candidates_after_year_filter": [c.dict() for c in candidates_after_year[:10]],  # Limit to first 10 for response size
                        "candidates_after_brand_filter": [c.dict() for c in candidates_after_brand[:10]],  # Limit to first 10 for response size
                        "performance": {
                            "total_search_time_ms": search_time,
                            "year_filtering_time_ms": year_filter_time,
                            "brand_filtering_time_ms": brand_filter_time
                        },
                        "statistics": {
                            "candidates_filtered_by_brand": candidates_filtered_by_brand,
                            "candidates_before_brand_filter": total_candidates_before_brand
                        }
                    }

                return final_candidates, debug_info

            except Exception as e:
                print(f"❌ Cache search failed: {e}")
                raise RuntimeError(f"Cache search error: {e}")

    def _calculate_fuzzy_score(self, query_label: str, catalog_label: str) -> float:
        """Calculate fuzzy string similarity score."""
        return fuzz.ratio(query_label.upper(), catalog_label.upper()) / 100.0

    def is_cache_available(self) -> bool:
        """Check if cache is loaded and available."""
        return self.settings.cache_enabled and self._is_loaded and len(self._catalog_data) > 0

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        with self._cache_lock:
            memory_usage = 0
            if self._embeddings is not None:
                memory_usage = (self._embeddings.nbytes + len(self._catalog_data) * 500) / 1024 / 1024

            return {
                "cache_enabled": self.settings.cache_enabled,
                "cache_loaded": self._is_loaded,
                "record_count": len(self._catalog_data),
                "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                "memory_usage_mb": round(memory_usage, 2),
                "should_refresh": self.should_refresh_cache(),
                "embedding_dimension": self._embeddings.shape[1] if self._embeddings is not None else 0
            }

    def get_health_status(self) -> Dict:
        """Get cache health status."""
        try:
            stats = self.get_cache_stats()
            return {
                "cache_healthy": self.is_cache_available(),
                "cache_enabled": stats["cache_enabled"],
                "cache_loaded": stats["cache_loaded"],
                "record_count": stats["record_count"],
                "memory_usage_mb": stats["memory_usage_mb"],
                "last_refresh": stats["last_refresh"],
                "needs_refresh": stats["should_refresh"]
            }
        except Exception as e:
            return {
                "cache_healthy": False,
                "error": str(e)
            }