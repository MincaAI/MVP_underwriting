"""Candidate matching using hybrid cache and database approach."""

import re
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from ..models import Candidate, ExtractedFields
from .cache import VehicleCatalogCache
from ..config import Settings


class CandidateMatcher:
    """Handles candidate search and matching using hybrid approach."""

    def __init__(self, engine, cache: VehicleCatalogCache, settings: Settings):
        """Initialize the candidate matcher."""
        self.engine = engine
        self.cache = cache
        self.settings = settings

    def find_candidates_hybrid(
        self, description: str, fields: ExtractedFields, modelo: int, embedding: List[float]
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Find candidates using hybrid approach: cache first, database fallback."""

        # Check if cache should be refreshed
        if self.cache.should_refresh_cache():
            print("🔄 Cache refresh needed, refreshing in background...")
            self.cache.refresh_cache()

        # Try cache first (only if we have a valid embedding)
        if self.cache.is_cache_available() and embedding is not None:
            try:
                print("🚀 Using in-memory cache for matching...")
                # Use exact year or range based on variance setting
                if self.settings.year_variance == 0:
                    year_min = year_max = modelo
                else:
                    year_min = modelo - self.settings.year_variance
                    year_max = modelo + self.settings.year_variance

                return self.cache.find_candidates_cached(
                    query_embedding=embedding,
                    query_label=description,
                    year_min=year_min,
                    year_max=year_max,
                    brand_filter=None  # No brand filtering at cache level
                )
            except Exception as e:
                print(f"⚠️ Cache search failed, falling back to database: {e}")
                # Fall through to database search
        elif self.cache.is_cache_available() and embedding is None:
            print("⚠️ Cache available but no embedding generated, using database fallback...")

        # Database fallback
        print("🗄️ Using database fallback for matching...")
        if embedding is not None:
            return self._find_candidates_with_embedding(description, fields, modelo, embedding)
        else:
            print("🔍 No embedding available, using fallback query without embeddings...")
            return self.find_candidates_fallback(fields, modelo)

    def _find_candidates_with_embedding(
        self, description: str, fields: ExtractedFields, modelo: int, embedding: List[float]
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Find candidates using pgvector similarity search."""
        # Build SQL query with vector similarity + year filter only (no brand filtering)
        sql_params = {
            'qvec': str(embedding),
            'year': modelo
        }

        # Build SQL with year filter
        where_conditions = [
            "catalog_version = (SELECT version FROM catalog_import WHERE status IN ('ACTIVE', 'LOADED') ORDER BY version DESC LIMIT 1)",
            "embedding IS NOT NULL"
        ]

        # Use exact year matching or range based on variance setting
        if modelo is not None:
            if self.settings.year_variance == 0:
                where_conditions.append("modelo = :year")
            else:
                sql_params['ymin'] = modelo - self.settings.year_variance
                sql_params['ymax'] = modelo + self.settings.year_variance
                where_conditions.append("modelo BETWEEN :ymin AND :ymax")

        # Brand filtering removed - now handled in dynamic filtering pipeline

        sql = f"""
        SELECT cvegs, marca, submarca, modelo, descveh, label, cvesegm, tipveh,
               1 - (embedding <=> CAST(:qvec AS vector)) AS similarity_score
        FROM amis_catalog
        WHERE {' AND '.join(where_conditions)}
        ORDER BY embedding <=> CAST(:qvec AS vector)
        LIMIT :limit
        """

        sql_params['limit'] = self.settings.max_candidates

        with Session(self.engine) as session:
            result = session.execute(text(sql), sql_params)
            rows = result.fetchall()

        # Convert to candidates with enhanced multi-factor scoring
        candidates = []
        for row in rows:
            # Calculate all scoring factors
            fuzzy_score = self._calculate_fuzzy_score(description, row.label or "")
            brand_score = self._calculate_brand_match_score(fields, row.marca)
            year_score = self._calculate_year_proximity_score(modelo, row.modelo)
            type_score = self._calculate_type_match_score(fields, row.descveh)

            # Enhanced multi-factor final score
            final_score = (
                self.settings.weight_embedding * row.similarity_score +
                self.settings.weight_fuzzy * fuzzy_score +
                self.settings.weight_brand_match * brand_score +
                self.settings.weight_year_proximity * year_score +
                self.settings.weight_type_match * type_score
            )

            candidates.append(Candidate(
                cvegs=row.cvegs,
                marca=row.marca,
                submarca=row.submarca,
                modelo=row.modelo,
                descveh=row.descveh,
                label=row.label,
                similarity_score=row.similarity_score,
                fuzzy_score=fuzzy_score,
                final_score=final_score,
                cvesegm=row.cvesegm,
                tipveh=row.tipveh
            ))

        # Re-sort by final hybrid score
        candidates.sort(key=lambda x: x.final_score, reverse=True)

        # Prepare debug information if enabled
        debug_info = None
        if self.settings.enable_debug_filtering:
            debug_info = {
                "filtering_steps": {
                    "total_candidates_from_database": len(candidates),
                    "after_scoring_and_limit": len(candidates)  # Already limited by SQL LIMIT
                },
                "applied_filters": {
                    "year": modelo,
                    "brand_filtering": "moved_to_dynamic_pipeline"
                },
                "database_query": {
                    "sql_conditions": where_conditions,
                    "sql_params": {k: v for k, v in sql_params.items() if k != 'qvec'}  # Exclude embedding vector for readability
                },
                "candidates_from_database": [c.dict() for c in candidates[:10]]  # Limit to first 10 for response size
            }

        return candidates, debug_info

    def find_candidates_fallback(
        self, fields: ExtractedFields, modelo: int
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Fallback candidate search without embeddings."""

        sql_params = {
            'year': modelo if modelo else None
        }

        # Build SQL dynamically based on available filters (only marca and modelo)
        where_conditions = [
            "catalog_version = (SELECT version FROM catalog_import WHERE status IN ('ACTIVE', 'LOADED') ORDER BY version DESC LIMIT 1)"
        ]

        if sql_params['year']:
            where_conditions.append("modelo = :year")
        # Brand filtering removed - now handled in dynamic filtering pipeline

        # If we have extracted brand info, prioritize that brand
        if fields.marca:
            sql = f"""
            SELECT cvegs, marca, submarca, modelo, descveh, label, cvesegm, tipveh
            FROM amis_catalog
            WHERE {' AND '.join(where_conditions)}
            ORDER BY
                CASE WHEN marca ILIKE :marca_priority THEN 0 ELSE 1 END,
                marca, submarca, modelo
            LIMIT :limit
            """
            sql_params['marca_priority'] = fields.marca
        else:
            sql = f"""
            SELECT cvegs, marca, submarca, modelo, descveh, label, cvesegm, tipveh
            FROM amis_catalog
            WHERE {' AND '.join(where_conditions)}
            ORDER BY marca, submarca, modelo
            LIMIT :limit
            """

        sql_params['limit'] = self.settings.max_candidates

        with Session(self.engine) as session:
            result = session.execute(text(sql), sql_params)
            rows = result.fetchall()

        # Create candidates with fuzzy scoring only (using only marca and modelo)
        candidates = []
        query_text = f"{fields.marca or ''} {modelo or ''}".strip()

        for row in rows:
            catalog_text = f"{row.marca} {row.submarca} {row.modelo}"
            fuzzy_score = fuzz.ratio(query_text.lower(), catalog_text.lower()) / 100.0

            candidates.append(Candidate(
                cvegs=row.cvegs,
                marca=row.marca,
                submarca=row.submarca,
                modelo=row.modelo,
                descveh=row.descveh,
                label=row.label,
                similarity_score=0.0,  # No embedding similarity available
                fuzzy_score=fuzzy_score,
                final_score=fuzzy_score,
                cvesegm=row.cvesegm,
                tipveh=row.tipveh
            ))

        candidates.sort(key=lambda x: x.final_score, reverse=True)

        # Prepare debug information if enabled
        debug_info = None
        if self.settings.enable_debug_filtering:
            debug_info = {
                "filtering_steps": {
                    "total_candidates_from_database": len(candidates),
                    "after_scoring_and_limit": len(candidates)  # Already limited by SQL LIMIT
                },
                "applied_filters": {
                    "year": modelo,
                    "brand_filtering": "moved_to_dynamic_pipeline"
                },
                "database_query": {
                    "sql_conditions": where_conditions,
                    "sql_params": sql_params
                },
                "candidates_from_database": [c.dict() for c in candidates[:10]]  # Limit to first 10 for response size
            }

        return candidates, debug_info

    def _calculate_fuzzy_score(self, description: str, catalog_label: str) -> float:
        """Calculate vehicle-aware fuzzy string similarity score."""
        query_clean = self._normalize_vehicle_text(description.lower())
        catalog_clean = self._normalize_vehicle_text((catalog_label or "").lower())

        # Use multiple fuzzy algorithms and take the best score
        ratio_score = fuzz.ratio(query_clean, catalog_clean) / 100.0
        partial_score = fuzz.partial_ratio(query_clean, catalog_clean) / 100.0
        token_sort_score = fuzz.token_sort_ratio(query_clean, catalog_clean) / 100.0

        # Weight the scores (ratio for overall, partial for substring, token_sort for word order)
        weighted_score = (
            0.5 * ratio_score +
            0.3 * partial_score +
            0.2 * token_sort_score
        )

        return weighted_score

    def _normalize_vehicle_text(self, text: str) -> str:
        """Normalize vehicle text for better fuzzy matching."""
        # Remove extra whitespace and special characters
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\w\s]', ' ', text)

        # Common vehicle term normalizations
        normalizations = {
            # Brand standardizations
            'volkswagen': 'vw',
            'chevrolet': 'chevy',
            'mercedes-benz': 'mercedes',
            'mercedes benz': 'mercedes',
            'bmw': 'bmw',

            # Model standardizations
            'tracto': 'tractor',
            'camioneta': 'pickup',
            'automovil': 'auto',
            'motocicleta': 'motorcycle',

            # Year normalizations
            'modelo': 'model',
            'año': 'year',

            # Remove common noise words
            'tr ': '',
            'veh ': '',
            'unidad ': '',
        }

        for old_term, new_term in normalizations.items():
            text = text.replace(old_term, new_term)

        # Remove extra spaces again after replacements
        text = re.sub(r'\s+', ' ', text.strip())

        return text

    def _calculate_brand_match_score(self, fields: ExtractedFields, catalog_marca: str) -> float:
        """Calculate brand exact match bonus score."""
        if not fields.marca or not catalog_marca:
            return 0.0

        query_brand = fields.marca.lower().strip()
        catalog_brand = catalog_marca.lower().strip()

        # Exact match bonus
        if query_brand == catalog_brand:
            return 1.0

        # Partial match for common abbreviations/variations
        if query_brand in catalog_brand or catalog_brand in query_brand:
            return 0.5

        return 0.0

    def _calculate_year_proximity_score(self, query_year: int, catalog_year: int) -> float:
        """Calculate year proximity bonus score."""
        if not query_year or not catalog_year:
            return 0.0

        year_diff = abs(query_year - catalog_year)

        # Perfect match
        if year_diff == 0:
            return 1.0
        # Close years (within variance)
        elif year_diff <= self.settings.year_variance:
            return 1.0 - (year_diff / self.settings.year_variance) * 0.5
        # Distant years
        else:
            return 0.0

    def _calculate_type_match_score(self, fields: ExtractedFields, catalog_descveh: str) -> float:
        """Calculate vehicle type match bonus score."""
        if not fields.tipveh or not catalog_descveh:
            return 0.0

        query_type = fields.tipveh.lower().strip()
        catalog_desc = catalog_descveh.lower().strip()

        # Vehicle type mapping for better matching
        type_keywords = {
            'auto': ['sedan', 'hatchback', 'coupe', 'convertible'],
            'camioneta': ['pickup', 'truck', 'tracto', 'trailer', 'cargo'],
            'motocicleta': ['motorcycle', 'moto', 'scooter'],
            'suv': ['suv', 'crossover', 'jeep']
        }

        # Direct type match in description
        if query_type in catalog_desc:
            return 1.0

        # Check type keywords
        for veh_type, keywords in type_keywords.items():
            if query_type == veh_type:
                for keyword in keywords:
                    if keyword in catalog_desc:
                        return 0.8

        return 0.0

    def find_candidates_prefiltered_semantic(
        self, description: str, prefiltered_candidates: List[Candidate], embedding: List[float]
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Re-rank pre-filtered candidates using semantic similarity."""
        import time
        import numpy as np

        print(f"🐛 DEBUG: find_candidates_prefiltered_semantic called with {len(prefiltered_candidates)} candidates")

        if not prefiltered_candidates or not embedding:
            print(f"🐛 DEBUG: Early return - no candidates or embedding")
            return prefiltered_candidates, None

        start_time = time.time()

        # Extract CVEGS IDs from pre-filtered candidates
        cvegs_ids = [str(candidate.cvegs) for candidate in prefiltered_candidates]

        if not cvegs_ids:
            return prefiltered_candidates, None

        # Create SQL to fetch embeddings for specific CVEGS IDs
        cvegs_placeholders = ','.join([f':cvegs_{i}' for i in range(len(cvegs_ids))])
        sql_params = {f'cvegs_{i}': cvegs_id for i, cvegs_id in enumerate(cvegs_ids)}

        sql = f"""
        SELECT cvegs, embedding
        FROM amis_catalog
        WHERE cvegs IN ({cvegs_placeholders})
          AND embedding IS NOT NULL
          AND catalog_version = (
              SELECT version FROM catalog_import
              WHERE status IN ('ACTIVE', 'LOADED')
              ORDER BY version DESC LIMIT 1
          )
        """

        try:
            with Session(self.engine) as session:
                result = session.execute(text(sql), sql_params)
                rows = result.fetchall()

                # Build mapping of CVEGS to embeddings
                cvegs_embeddings = {}
                for row in rows:
                    try:
                        # Parse embedding from string format
                        embedding_str = row.embedding.strip('[]')
                        embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                        cvegs_embeddings[row.cvegs] = np.array(embedding_values, dtype=np.float32)
                    except (ValueError, AttributeError) as e:
                        print(f"⚠️ Skipping embedding for CVEGS {row.cvegs}: {e}")
                        continue

                if not cvegs_embeddings:
                    print(f"⚠️ No valid embeddings found for pre-filtered candidates")
                    return prefiltered_candidates, None

                # Convert query embedding to numpy array and normalize
                query_vec = np.array(embedding, dtype=np.float32)
                query_vec = query_vec / np.linalg.norm(query_vec)

                # Calculate similarities and update candidates
                updated_candidates = []
                similarities_calculated = 0

                for candidate in prefiltered_candidates:
                    if candidate.cvegs in cvegs_embeddings:
                        # Get candidate embedding and normalize
                        candidate_embedding = cvegs_embeddings[candidate.cvegs]
                        candidate_embedding = candidate_embedding / np.linalg.norm(candidate_embedding)

                        # Calculate cosine similarity
                        similarity_score = float(np.dot(query_vec, candidate_embedding))
                        similarities_calculated += 1

                        # Calculate enhanced fuzzy score using description
                        fuzzy_score = self._calculate_fuzzy_score(description, candidate.label or "")

                        # Enhanced multi-factor final score
                        final_score = (
                            self.settings.weight_embedding * similarity_score +
                            self.settings.weight_fuzzy * fuzzy_score +
                            candidate.final_score * 0.1  # Small bonus for original filtering score
                        )

                        # Create updated candidate with semantic scores
                        updated_candidate = Candidate(
                            cvegs=candidate.cvegs,
                            marca=candidate.marca,
                            submarca=candidate.submarca,
                            modelo=candidate.modelo,
                            descveh=candidate.descveh,
                            label=candidate.label,
                            similarity_score=similarity_score,
                            fuzzy_score=fuzzy_score,
                            final_score=final_score,
                            cvesegm=candidate.cvesegm,
                            tipveh=candidate.tipveh
                        )
                        updated_candidates.append(updated_candidate)
                    else:
                        # Keep original candidate if no embedding available
                        updated_candidates.append(candidate)

                # Sort by final score
                updated_candidates.sort(key=lambda x: x.final_score, reverse=True)

                search_time = (time.time() - start_time) * 1000

                print(f"🚀 Prefiltered semantic re-ranking: {similarities_calculated}/{len(prefiltered_candidates)} candidates with embeddings, {search_time:.2f}ms")

                # Prepare debug information
                debug_info = {
                    "prefiltered_semantic_search": {
                        "input_candidates": len(prefiltered_candidates),
                        "candidates_with_embeddings": similarities_calculated,
                        "search_time_ms": search_time,
                        "performance_gain": f"~{84163/len(prefiltered_candidates):.0f}x faster than full catalog search"
                    },
                    "top_candidates_after_semantic_rerank": [c.dict() for c in updated_candidates[:5]]
                }

                return updated_candidates, debug_info

        except Exception as e:
            print(f"❌ Prefiltered semantic search failed: {e}")
            # Return original candidates on error
            return prefiltered_candidates, None

    def find_candidates_embedding_only(
        self, description: str, year: int, embedding: List[float], prefiltered_candidates: Optional[List[Candidate]] = None
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Find top candidates using only embedding similarity (no hybrid scoring)."""
        import time
        import numpy as np

        if not embedding:
            return [], None

        start_time = time.time()

        # If we have prefiltered candidates, rank them by embedding only
        if prefiltered_candidates:
            print(f"🎯 Ranking {len(prefiltered_candidates)} prefiltered candidates by embedding similarity only")
            return self._rank_prefiltered_by_embedding(prefiltered_candidates, embedding, start_time)

        # Otherwise do full catalog search by embedding only
        print(f"🔍 Full catalog search by embedding similarity only (top {self.settings.embedding_only_candidates})")
        return self._full_catalog_embedding_search(description, year, embedding, start_time)

    def _rank_prefiltered_by_embedding(
        self, prefiltered_candidates: List[Candidate], embedding: List[float], start_time: float
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Rank prefiltered candidates by embedding similarity only."""
        import time
        import numpy as np

        # Extract CVEGS IDs from pre-filtered candidates
        cvegs_ids = [str(candidate.cvegs) for candidate in prefiltered_candidates]

        # Create SQL to fetch embeddings for specific CVEGS IDs
        cvegs_placeholders = ','.join([f':cvegs_{i}' for i in range(len(cvegs_ids))])
        sql_params = {f'cvegs_{i}': cvegs_id for i, cvegs_id in enumerate(cvegs_ids)}

        sql = f"""
        SELECT cvegs, embedding
        FROM amis_catalog
        WHERE cvegs IN ({cvegs_placeholders})
          AND embedding IS NOT NULL
          AND catalog_version = (
              SELECT version FROM catalog_import
              WHERE status IN ('ACTIVE', 'LOADED')
              ORDER BY version DESC LIMIT 1
          )
        """

        try:
            with Session(self.engine) as session:
                result = session.execute(text(sql), sql_params)
                rows = result.fetchall()

                # Build mapping of CVEGS to embeddings
                cvegs_embeddings = {}
                for row in rows:
                    try:
                        # Parse embedding from string format
                        embedding_str = row.embedding.strip('[]')
                        embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                        cvegs_embeddings[row.cvegs] = np.array(embedding_values, dtype=np.float32)
                    except (ValueError, AttributeError) as e:
                        print(f"⚠️ Skipping embedding for CVEGS {row.cvegs}: {e}")
                        continue

                if not cvegs_embeddings:
                    print(f"⚠️ No valid embeddings found for prefiltered candidates")
                    return prefiltered_candidates, None

                # Convert query embedding to numpy array and normalize
                query_vec = np.array(embedding, dtype=np.float32)
                query_vec = query_vec / np.linalg.norm(query_vec)

                # Calculate similarities and update candidates
                updated_candidates = []
                similarities_calculated = 0

                for candidate in prefiltered_candidates:
                    if candidate.cvegs in cvegs_embeddings:
                        # Get candidate embedding and normalize
                        candidate_embedding = cvegs_embeddings[candidate.cvegs]
                        candidate_embedding = candidate_embedding / np.linalg.norm(candidate_embedding)

                        # Calculate cosine similarity (range: [-1, 1])
                        raw_similarity = float(np.dot(query_vec, candidate_embedding))

                        # Normalize to [0, 1] range: (similarity + 1) / 2
                        similarity_score = (raw_similarity + 1.0) / 2.0
                        similarities_calculated += 1

                        # Create candidate with only embedding score (no hybrid scoring)
                        updated_candidate = Candidate(
                            cvegs=candidate.cvegs,
                            marca=candidate.marca,
                            submarca=candidate.submarca,
                            modelo=candidate.modelo,
                            descveh=candidate.descveh,
                            label=candidate.label,
                            similarity_score=similarity_score,
                            fuzzy_score=0.0,  # Not used in embedding-only approach
                            final_score=similarity_score,  # Final score = normalized embedding score
                            cvesegm=candidate.cvesegm,
                            tipveh=candidate.tipveh
                        )
                        updated_candidates.append(updated_candidate)
                    else:
                        # Keep original candidate if no embedding available (with score 0)
                        candidate.similarity_score = 0.0
                        candidate.final_score = 0.0
                        updated_candidates.append(candidate)

                # Sort by embedding similarity only
                updated_candidates.sort(key=lambda x: x.similarity_score, reverse=True)

                # Take top embedding_only_candidates
                final_candidates = updated_candidates[:self.settings.embedding_only_candidates]

                search_time = (time.time() - start_time) * 1000

                print(f"🎯 Embedding-only ranking: {similarities_calculated}/{len(prefiltered_candidates)} candidates with embeddings, {search_time:.2f}ms")

                # Prepare debug information
                debug_info = {
                    "embedding_only_search": {
                        "input_candidates": len(prefiltered_candidates),
                        "candidates_with_embeddings": similarities_calculated,
                        "output_candidates": len(final_candidates),
                        "search_time_ms": search_time,
                        "approach": "prefiltered_embedding_ranking"
                    },
                    "top_candidates_by_embedding": [c.dict() for c in final_candidates[:5]]
                }

                return final_candidates, debug_info

        except Exception as e:
            print(f"❌ Prefiltered embedding ranking failed: {e}")
            # Return original candidates on error
            return prefiltered_candidates, None

    def _full_catalog_embedding_search(
        self, description: str, year: int, embedding: List[float], start_time: float
    ) -> Tuple[List[Candidate], Optional[Dict[str, Any]]]:
        """Search full catalog by embedding similarity only."""

        # Build SQL query with only embedding similarity
        sql_params = {
            'qvec': str(embedding),
            'year': year,
            'limit': self.settings.embedding_only_candidates
        }

        # Build SQL with year filter
        where_conditions = [
            "catalog_version = (SELECT version FROM catalog_import WHERE status IN ('ACTIVE', 'LOADED') ORDER BY version DESC LIMIT 1)",
            "embedding IS NOT NULL"
        ]

        # Use exact year matching or range based on variance setting
        if year is not None:
            if self.settings.year_variance == 0:
                where_conditions.append("modelo = :year")
            else:
                sql_params['ymin'] = year - self.settings.year_variance
                sql_params['ymax'] = year + self.settings.year_variance
                where_conditions.append("modelo BETWEEN :ymin AND :ymax")

        sql = f"""
        SELECT cvegs, marca, submarca, modelo, descveh, label, cvesegm, tipveh,
               1 - (embedding <=> CAST(:qvec AS vector)) AS similarity_score
        FROM amis_catalog
        WHERE {' AND '.join(where_conditions)}
        ORDER BY embedding <=> CAST(:qvec AS vector)
        LIMIT :limit
        """

        try:
            with Session(self.engine) as session:
                result = session.execute(text(sql), sql_params)
                rows = result.fetchall()

            # Convert to candidates with only embedding scores
            candidates = []
            for row in rows:
                candidates.append(Candidate(
                    cvegs=row.cvegs,
                    marca=row.marca,
                    submarca=row.submarca,
                    modelo=row.modelo,
                    descveh=row.descveh,
                    label=row.label,
                    similarity_score=row.similarity_score,
                    fuzzy_score=0.0,  # Not used in embedding-only approach
                    final_score=row.similarity_score,  # Final score = embedding score
                    cvesegm=row.cvesegm,
                    tipveh=row.tipveh
                ))

            search_time = (time.time() - start_time) * 1000

            print(f"🔍 Full catalog embedding search: {len(candidates)} candidates, {search_time:.2f}ms")

            # Prepare debug information
            debug_info = {
                "embedding_only_search": {
                    "approach": "full_catalog_embedding",
                    "output_candidates": len(candidates),
                    "search_time_ms": search_time,
                    "sql_conditions": where_conditions
                },
                "top_candidates_by_embedding": [c.dict() for c in candidates[:5]]
            }

            return candidates, debug_info

        except Exception as e:
            print(f"❌ Full catalog embedding search failed: {e}")
            return [], None