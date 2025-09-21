"""Core vehicle codification service with pgvector similarity search."""

import time
import json
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import numpy as np
from rapidfuzz import fuzz
import openai

from .config import get_settings
from .models import VehicleInput, MatchResult, Candidate, ExtractedFields, ReviewCandidate
from .preprocessor import VehiclePreprocessor
from .extractor import VehicleExtractor
from .label_builder import VehicleLabelBuilder
from .cache import VehicleCatalogCache


class VehicleCodeifier:
    """Simplified vehicle codification service using pgvector similarity."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)
        self.preprocessor = VehiclePreprocessor()
        self.extractor = VehicleExtractor()
        self.label_builder = VehicleLabelBuilder()
        self.cache = VehicleCatalogCache()

        # Dynamic filtering is now handled directly in Step 3 pre-filtering

        # Initialize OpenAI client for LLM validation
        self.openai_client = None
        if self.settings.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.settings.openai_api_key)

    def match_vehicle(self, vehicle_input: VehicleInput) -> MatchResult:
        """Match a single vehicle against the CATVER catalog."""
        start_time = time.time()

        try:
            # Step 1: Preprocess input (smart field detection and normalization)
            raw_input = {"modelo": vehicle_input.modelo, "description": vehicle_input.description}
            processed_batch = self.preprocessor.process(raw_input)
            processed = processed_batch["0"]  # Extract single row from batch result

            # Step 2: Extract CATVER fields from normalized description
            year = processed["model_year"]
            extracted_fields_with_confidence = self.extractor.extract_fields_with_confidence(processed["description"], year)

            print('===>', extracted_fields_with_confidence);
            # Step 3: Apply high-confidence filters directly (OPTIMIZED)
            print("🔧 Step 3: Applying high-confidence filters directly...")

            pre_filtered_candidates, total_before_filtering, dynamic_filter_results = self._find_candidates_with_high_confidence_filters(
                extracted_fields_with_confidence, processed["model_year"]
            )

            if total_before_filtering > 0:
                reduction_ratio = len(pre_filtered_candidates) / total_before_filtering
                print(f"🎯 Direct filtering result: {len(pre_filtered_candidates)} candidates remain ({reduction_ratio:.2%} of original)")

            # Step 4: Use pre-filtered candidates directly or fallback to database search
            debug_info = None
            if pre_filtered_candidates:
                # Use pre-filtered candidates directly
                candidates = pre_filtered_candidates
                debug_info = {
                    "search_method": "pre_filtered_only",
                    "pre_filter_count": len(pre_filtered_candidates),
                    "skipped_embedding": True
                }
                print(f"📊 Using {len(candidates)} pre-filtered candidates directly")
                print(f"📊 DEBUG: Candidates before LLM validation: {len(candidates)}")
                if candidates:
                    for i, c in enumerate(candidates[:3]):
                        print(f"   {i+1}. {c.marca} {c.submarca} (final_score: {c.final_score})")
            else:
                # Fallback to database search without embeddings
                candidates, debug_info = self._find_candidates_fallback(extracted_fields, processed["model_year"])
                print(f"📊 Fallback search returned {len(candidates)} candidates")

            # Step 5: LLM validation of candidates (MOVED UP)
            print(f"🔍 DEBUG: About to check LLM validation - OpenAI client: {self.openai_client is not None}, Candidates: {len(candidates)}")
            if self.openai_client and candidates:
                candidates = self._llm_validate_candidates(
                    candidates, processed["description"], extracted_fields, processed["model_year"]
                )
                print(f"📊 DEBUG: Candidates after LLM validation: {len(candidates)}")
                if candidates:
                    for i, c in enumerate(candidates[:3]):
                        print(f"   {i+1}. {c.marca} {c.submarca} (final_score: {c.final_score})")
                else:
                    print("   ⚠️ All candidates were removed by LLM validation")
            else:
                print(f"⚠️ Skipping LLM validation - OpenAI client: {self.openai_client is not None}, Candidates: {len(candidates)}")

            # Add dynamic filtering info to debug
            if debug_info and self.settings.enable_debug_filtering and dynamic_filter_results:
                debug_info["dynamic_filtering"] = {
                    "enabled": True,
                    "method": "high_confidence_direct_sql",
                    "applied_early": True,
                    "applied_before_embedding": True,
                    "total_before_filtering": total_before_filtering,
                    "total_after_filtering": len(pre_filtered_candidates),
                    "filters_applied": dynamic_filter_results
                }

            # Step 6: Apply decision thresholds
            print(f"🔍 DEBUG: About to make decision with {len(candidates)} candidates")
            if candidates:
                for i, c in enumerate(candidates[:3]):
                    print(f"   {i+1}. {c.marca} {c.submarca} (final_score: {c.final_score})")
            decision, confidence, suggested_cvegs = self._make_decision(candidates, extracted_fields)
            print(f"🔍 DEBUG: Decision made - decision: {decision}, confidence: {confidence}, suggested_cvegs: {suggested_cvegs}")

            # Step 7: Create enhanced response with review candidates
            top_candidates_for_review = self._create_review_candidates(candidates, decision)
            recommendation = self._get_recommendation(decision, confidence)

            processing_time_ms = (time.time() - start_time) * 1000

            # Create simple query label for response
            query_label = f"{processed['model_year']} {extracted_fields.marca or ''} {extracted_fields.submarca or ''}".strip()

            return MatchResult(
                success=decision != "no_match",
                decision=decision,
                confidence=confidence,
                suggested_cvegs=suggested_cvegs,
                candidates=candidates[:self.settings.max_results],
                extracted_fields=extracted_fields,
                processing_time_ms=processing_time_ms,
                query_label=query_label,
                top_candidates_for_review=top_candidates_for_review,
                recommendation=recommendation,
                debug_info=debug_info if self.settings.enable_debug_filtering else None
            )

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            return MatchResult(
                success=False,
                decision="no_match",
                confidence=0.0,
                candidates=[],
                processing_time_ms=processing_time_ms,
                query_label=f"Error: {str(e)}"
            )

    def _find_candidates_hybrid(
        self, query_label: str, fields: ExtractedFields, modelo: int, embedding: List[float]
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
                    query_label=query_label,
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
            return self._find_candidates_with_embedding(query_label, fields, modelo, embedding)
        else:
            print("🔍 No embedding available, using fallback query without embeddings...")
            return self._find_candidates_fallback(fields, modelo)

    def _find_candidates_with_embedding(
        self, query_label: str, fields: ExtractedFields, modelo: int, embedding: List[float]
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
        SELECT cvegs, marca, submarca, modelo, descveh, label,
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
            fuzzy_score = self._calculate_fuzzy_score(query_label, row.label)
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
                final_score=final_score
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

    def _find_candidates_fallback(
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
            SELECT cvegs, marca, submarca, modelo, descveh, label
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
            SELECT cvegs, marca, submarca, modelo, descveh, label
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
                final_score=fuzzy_score
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

    def _calculate_fuzzy_score(self, query_label: str, catalog_label: str) -> float:
        """Calculate vehicle-aware fuzzy string similarity score."""
        query_clean = self._normalize_vehicle_text(query_label.upper())
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
        import re

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

    def _make_decision(self, candidates: List[Candidate], fields: ExtractedFields) -> Tuple[str, float, Optional[int]]:
        """Apply dynamic decision thresholds based on vehicle type."""
        if not candidates:
            return "no_match", 0.0, None

        best_candidate = candidates[0]
        confidence = best_candidate.final_score

        # Get dynamic thresholds based on vehicle type
        thresholds = self._get_dynamic_thresholds(fields.tipveh)
        threshold_high = thresholds["high"]
        threshold_low = thresholds["low"]

        if confidence >= threshold_high:
            return "auto_accept", confidence, best_candidate.cvegs
        elif confidence >= threshold_low:
            return "needs_review", confidence, best_candidate.cvegs
        else:
            return "no_match", confidence, None

    def _get_dynamic_thresholds(self, vehicle_type: Optional[str]) -> dict:
        """Get dynamic thresholds based on vehicle type."""
        if not vehicle_type:
            return self.settings.thresholds_by_type["default"]

        vehicle_type_clean = vehicle_type.upper().strip()

        # Map vehicle types to threshold categories
        if vehicle_type_clean in ["auto", "sedan", "hatchback", "coupe"]:
            return self.settings.thresholds_by_type["auto"]
        elif vehicle_type_clean in ["camioneta", "pickup", "truck", "tracto", "trailer"]:
            return self.settings.thresholds_by_type["camioneta"]
        elif vehicle_type_clean in ["motocicleta", "motorcycle", "moto"]:
            return self.settings.thresholds_by_type["motocicleta"]
        else:
            return self.settings.thresholds_by_type["default"]

    def _llm_validate_candidates(self, candidates: List[Candidate], description: str,
                                extracted_fields: ExtractedFields, year: int) -> List[Candidate]:
        """Use LLM to validate and score candidates with confidence ratings."""
        if not self.openai_client or not candidates:
            return candidates

        print(f"🤖 Step 4: LLM validation of {len(candidates)} candidates...")

        # Check if these are high-confidence pre-filtered candidates
        # High-confidence candidates should be trusted more and not easily discarded
        has_high_confidence_candidates = any(c.final_score >= 0.9 for c in candidates)

        if has_high_confidence_candidates:
            print(f"🎯 Found high-confidence pre-filtered candidates (score >= 0.9), being more lenient")

        try:
            # Prepare candidates for LLM analysis
            candidate_info = []
            for i, candidate in enumerate(candidates):  # Limit to top 10 for efficiency
                candidate_info.append({
                    "index": i,
                    "cvegs": str(candidate.cvegs),
                    "brand": candidate.marca,
                    "submodel": candidate.submarca,
                    "year": candidate.modelo,
                    "description": candidate.descveh,
                    "current_score": round(candidate.final_score, 3)
                })

            prompt = f"""Analyze this vehicle description and rate how well each candidate matches.

Vehicle to match:
- Year: {year}
- Description: "{description}"
- Extracted brand: {extracted_fields.marca or 'None'}
- Extracted submodel: {extracted_fields.submarca or 'None'}
- Extracted type: {extracted_fields.tipveh or 'None'}

Candidates:
{json.dumps(candidate_info, indent=2)}

For each candidate, provide a confidence score (0.0-1.0) based on:
1. Brand match accuracy
2. Model/submodel compatibility
3. Year appropriateness
4. Vehicle type consistency
5. Overall description alignment

{"Note: These candidates were pre-filtered with high confidence (>=0.9), so be more lenient in scoring." if has_high_confidence_candidates else ""}

Return JSON format:
{{
  "validations": [
    {{"index": 0, "confidence": 0.85, "reasoning": "Strong brand and model match"}},
    {{"index": 1, "confidence": 0.65, "reasoning": "Brand matches but submodel differs"}}
  ]
}}"""

            response = self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result_data = json.loads(result_text)
                validations = result_data.get("validations", [])

                # Apply LLM confidence scores
                validated_candidates = []
                for validation in validations:
                    idx = validation.get("index")
                    llm_confidence = validation.get("confidence", 0.0)

                    if idx is not None and idx < len(candidates):
                        candidate = candidates[idx]

                        # For high-confidence pre-filtered candidates, be more conservative with LLM blending
                        if candidate.final_score >= 0.9:
                            # Trust the pre-filtering more: 80% original, 20% LLM
                            # Also ensure LLM confidence doesn't drop too much
                            min_llm_confidence = max(llm_confidence, 0.7)  # Don't let LLM go below 0.7 for high-confidence candidates
                            blended_score = (0.8 * candidate.final_score) + (0.2 * min_llm_confidence)
                            print(f"🎯 High-confidence candidate preserved: {candidate.marca} {candidate.submarca} (original: {candidate.final_score:.3f}, LLM: {llm_confidence:.3f}, final: {blended_score:.3f})")
                        else:
                            # Normal blending for regular candidates: 60% original, 40% LLM
                            blended_score = (0.6 * candidate.final_score) + (0.4 * llm_confidence)

                        # Create new candidate with updated score
                        validated_candidate = Candidate(
                            cvegs=candidate.cvegs,
                            marca=candidate.marca,
                            submarca=candidate.submarca,
                            modelo=candidate.modelo,
                            descveh=candidate.descveh,
                            label=candidate.label,
                            similarity_score=candidate.similarity_score,
                            fuzzy_score=candidate.fuzzy_score,
                            final_score=blended_score
                        )
                        validated_candidates.append(validated_candidate)

                # Add remaining candidates without LLM validation (preserve high-confidence ones)
                for i, candidate in enumerate(candidates):
                    if i >= len(validations):
                        # For high-confidence candidates without LLM validation, keep them with slight penalty
                        if candidate.final_score >= 0.9:
                            adjusted_candidate = Candidate(
                                cvegs=candidate.cvegs,
                                marca=candidate.marca,
                                submarca=candidate.submarca,
                                modelo=candidate.modelo,
                                descveh=candidate.descveh,
                                label=candidate.label,
                                similarity_score=candidate.similarity_score,
                                fuzzy_score=candidate.fuzzy_score,
                                final_score=candidate.final_score * 0.95  # Slight penalty for no LLM validation
                            )
                            validated_candidates.append(adjusted_candidate)
                            print(f"🎯 High-confidence candidate preserved without LLM validation: {candidate.marca} {candidate.submarca}")
                        else:
                            validated_candidates.append(candidate)

                # Re-sort by new blended scores
                validated_candidates.sort(key=lambda x: x.final_score, reverse=True)

                if validated_candidates:
                    print(f"✅ LLM validation completed. Top candidate score: {validated_candidates[0].final_score:.3f}")
                else:
                    print(f"⚠️ LLM validation removed all candidates")
                return validated_candidates

            except json.JSONDecodeError:
                print("⚠️ LLM returned invalid JSON, using original candidates")
                return candidates

        except Exception as e:
            print(f"⚠️ LLM validation failed: {e}")
            return candidates

    def _create_review_candidates(self, candidates: List[Candidate], decision: str) -> List[ReviewCandidate]:
        """Create review candidates for enhanced user experience."""
        if not self.settings.return_candidates_on_no_match and decision == "no_match":
            return []

        if not candidates:
            return []

        # Determine how many candidates to return
        num_candidates = min(
            len(candidates),
            self.settings.max_candidates_for_review if decision == "no_match"
            else self.settings.min_candidates_for_review
        )

        review_candidates = []
        for candidate in candidates[:num_candidates]:
            match_quality = self._determine_match_quality(candidate.final_score, decision)

            review_candidate = ReviewCandidate(
                cvegs=candidate.cvegs,
                marca=candidate.marca,
                submarca=candidate.submarca,
                modelo=candidate.modelo,
                descveh=candidate.descveh,
                confidence=candidate.final_score,
                match_quality=match_quality,
                similarity_score=candidate.similarity_score,
                fuzzy_score=candidate.fuzzy_score
            )
            review_candidates.append(review_candidate)

        return review_candidates

    def _determine_match_quality(self, confidence: float, decision: str) -> str:
        """Determine match quality based on confidence score and decision."""
        if decision == "auto_accept":
            return "high"
        elif decision == "needs_review":
            return "medium"
        else:  # no_match
            if confidence >= 0.4:
                return "medium"
            elif confidence >= 0.2:
                return "low"
            else:
                return "very_low"

    def _get_recommendation(self, decision: str, confidence: float) -> str:
        """Get recommendation for user action."""
        if decision == "auto_accept":
            return "use_suggested_cvegs"
        elif decision == "needs_review":
            return "manual_review_recommended"
        else:  # no_match
            if confidence >= 0.3:
                return "manual_review_suggested"
            else:
                return "manual_entry_may_be_needed"



    def _find_candidates_with_high_confidence_filters(self, extracted_fields_with_confidence, year: int) -> Tuple[List[Candidate], int, List[Dict]]:
        """Find candidates using high-confidence filters (≥0.9) directly in SQL."""

        # Build WHERE conditions based on high confidence scores (≥0.9)
        where_conditions = [
            "modelo = :year",
            "catalog_version = (SELECT version FROM catalog_import WHERE status IN ('ACTIVE', 'LOADED') ORDER BY version DESC LIMIT 1)"
        ]
        sql_params = {"year": year}
        applied_filters = []

        # Check each field for high confidence and add to SQL filter
        confidence_threshold = 0.9

        # Get total count before filtering (for reporting)
        total_before_filter = 0
        try:
            with Session(self.engine) as session:
                total_result = session.execute(text("""
                    SELECT COUNT(*) as total
                    FROM amis_catalog
                    WHERE modelo = :year
                      AND catalog_version = (
                          SELECT version FROM catalog_import
                          WHERE status IN ('ACTIVE', 'LOADED')
                          ORDER BY version DESC LIMIT 1
                      )
                """), {"year": year})
                total_before_filter = total_result.fetchone().total
        except Exception as e:
            print(f"⚠️ Error counting total candidates: {e}")
            total_before_filter = 0

        # Apply high-confidence filters
        if extracted_fields_with_confidence.marca.confidence >= confidence_threshold:
            where_conditions.append("marca = :marca")
            sql_params["marca"] = extracted_fields_with_confidence.marca.value
            applied_filters.append({
                "filter_name": "marca",
                "applied": True,
                "extracted_value": extracted_fields_with_confidence.marca.value,
                "confidence": extracted_fields_with_confidence.marca.confidence,
                "method": extracted_fields_with_confidence.marca.method
            })
            print(f"✅ Applying marca filter: '{extracted_fields_with_confidence.marca.value}' (confidence: {extracted_fields_with_confidence.marca.confidence:.2f})")

        if extracted_fields_with_confidence.tipveh.confidence >= confidence_threshold:
            where_conditions.append("tipveh = :tipveh")
            sql_params["tipveh"] = extracted_fields_with_confidence.tipveh.value
            applied_filters.append({
                "filter_name": "tipveh",
                "applied": True,
                "extracted_value": extracted_fields_with_confidence.tipveh.value,
                "confidence": extracted_fields_with_confidence.tipveh.confidence,
                "method": extracted_fields_with_confidence.tipveh.method
            })
            print(f"✅ Applying tipveh filter: '{extracted_fields_with_confidence.tipveh.value}' (confidence: {extracted_fields_with_confidence.tipveh.confidence:.2f})")

        if extracted_fields_with_confidence.cvesegm.confidence >= confidence_threshold:
            where_conditions.append("cvesegm = :cvesegm")
            sql_params["cvesegm"] = extracted_fields_with_confidence.cvesegm.value
            applied_filters.append({
                "filter_name": "cvesegm",
                "applied": True,
                "extracted_value": extracted_fields_with_confidence.cvesegm.value,
                "confidence": extracted_fields_with_confidence.cvesegm.confidence,
                "method": extracted_fields_with_confidence.cvesegm.method
            })
            print(f"✅ Applying cvesegm filter: '{extracted_fields_with_confidence.cvesegm.value}' (confidence: {extracted_fields_with_confidence.cvesegm.confidence:.2f})")

        if extracted_fields_with_confidence.submarca.confidence >= confidence_threshold:
            where_conditions.append("submarca = :submarca")
            sql_params["submarca"] = extracted_fields_with_confidence.submarca.value
            applied_filters.append({
                "filter_name": "submarca",
                "applied": True,
                "extracted_value": extracted_fields_with_confidence.submarca.value,
                "confidence": extracted_fields_with_confidence.submarca.confidence,
                "method": extracted_fields_with_confidence.submarca.method
            })
            print(f"✅ Applying submarca filter: '{extracted_fields_with_confidence.submarca.value}' (confidence: {extracted_fields_with_confidence.submarca.confidence:.2f})")

        # Execute filtered query
        candidates = []
        try:
            with Session(self.engine) as session:
                sql = f"""
                    SELECT cvegs, marca, submarca, modelo, descveh, cvesegm, tipveh
                    FROM amis_catalog
                    WHERE {' AND '.join(where_conditions)}
                    LIMIT 1000
                """

                result = session.execute(text(sql), sql_params)

                for row in result:
                    # Create label for candidate
                    label = f"{row.modelo} {row.marca} {row.submarca or ''} {row.cvesegm or ''} {row.tipveh or ''}".strip()

                    # Calculate confidence score based on number of high-confidence filters matched
                    # Since this candidate passed all applied high-confidence filters, assign high score
                    confidence_score = 0.0
                    filters_matched = len(applied_filters)

                    if filters_matched >= 3:  # 3+ high-confidence matches
                        confidence_score = 0.95
                    elif filters_matched == 2:  # 2 high-confidence matches
                        confidence_score = 0.85
                    elif filters_matched == 1:  # 1 high-confidence match
                        confidence_score = 0.75
                    else:  # Just year match
                        confidence_score = 0.50

                    candidates.append(Candidate(
                        cvegs=row.cvegs,
                        marca=row.marca,
                        submarca=row.submarca or "",
                        modelo=row.modelo,
                        descveh=row.descveh or "",
                        label=label,
                        similarity_score=confidence_score,  # Use confidence as similarity
                        fuzzy_score=confidence_score,       # Use confidence as fuzzy
                        final_score=confidence_score        # Use confidence as final score
                    ))

        except Exception as e:
            print(f"❌ Error executing filtered query: {e}")

        print(f"🎯 High-confidence filtering: {total_before_filter} → {len(candidates)} candidates")

        return candidates, total_before_filter, applied_filters



    def get_health_status(self) -> dict:
        """Get service health status."""
        try:
            with Session(self.engine) as session:
                # Check database connection
                session.execute(text("SELECT 1"))

                # Get active catalog info
                result = session.execute(text("""
                    SELECT ci.version, COUNT(ac.id) as record_count
                    FROM catalog_import ci
                    LEFT JOIN amis_catalog ac ON ac.catalog_version = ci.version
                    WHERE ci.status IN ('ACTIVE', 'LOADED')
                    GROUP BY ci.version
                    ORDER BY ci.version DESC
                    LIMIT 1
                """))

                row = result.fetchone()
                active_version = row.version if row else None
                record_count = row.record_count if row else 0

                # Get component health status
                preprocessor_health = self.preprocessor.get_health_status()
                extractor_health = self.extractor.get_health_status()
                label_builder_health = self.label_builder.get_health_status()
                cache_health = self.cache.get_health_status()

                return {
                    "status": "healthy",
                    "database_connected": True,
                    "active_catalog_version": active_version,
                    "catalog_records": record_count,
                    "embedding_model": label_builder_health["embedding_model"],
                    "embedder_available": label_builder_health["embedder_available"],
                    "openai_available": extractor_health["openai_available"],
                    "preprocessor_healthy": True,
                    "extractor_healthy": True,
                    "label_builder_healthy": True,
                    "cache_healthy": cache_health["cache_healthy"],
                    "cache_enabled": cache_health["cache_enabled"],
                    "cache_loaded": cache_health["cache_loaded"],
                    "cache_record_count": cache_health["record_count"],
                    "cache_memory_usage_mb": cache_health["memory_usage_mb"],
                    "cache_last_refresh": cache_health["last_refresh"],
                    "cache_needs_refresh": cache_health["needs_refresh"]
                }

        except Exception as e:
            extractor_health = self.extractor.get_health_status()
            label_builder_health = self.label_builder.get_health_status()
            cache_health = self.cache.get_health_status()
            return {
                "status": "unhealthy",
                "database_connected": False,
                "error": str(e),
                "embedding_model": label_builder_health["embedding_model"],
                "embedder_available": label_builder_health["embedder_available"],
                "openai_available": extractor_health["openai_available"],
                "preprocessor_healthy": False,
                "extractor_healthy": False,
                "label_builder_healthy": False,
                "cache_healthy": cache_health.get("cache_healthy", False),
                "cache_enabled": cache_health.get("cache_enabled", False),
                "cache_loaded": cache_health.get("cache_loaded", False)
            }