"""Candidate matching using hybrid cache and database approach."""

import re
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from .models import Candidate, ExtractedFields
from .cache import VehicleCatalogCache
from .config import Settings


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
            fuzzy_score = self._calculate_fuzzy_score(description, row.label)
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
            fuzzy_score = fuzz.ratio(query_text.upper(), catalog_text.upper()) / 100.0

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
        query_clean = self._normalize_vehicle_text(description.upper())
        catalog_clean = self._normalize_vehicle_text(catalog_label.upper())

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

        query_brand = fields.marca.upper().strip()
        catalog_brand = catalog_marca.upper().strip()

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

        query_type = fields.tipveh.upper().strip()
        catalog_desc = catalog_descveh.upper().strip()

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