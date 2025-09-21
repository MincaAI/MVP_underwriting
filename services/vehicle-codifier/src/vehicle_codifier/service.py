"""Core vehicle codification service with modular components."""

import time
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine
import openai

from .config import get_settings
from .models import VehicleInput, MatchResult, ExtractedFields
from .preprocessor import VehiclePreprocessor
from .extractor import VehicleExtractor
from .label_builder import VehicleLabelBuilder
from .cache import VehicleCatalogCache
from .candidate_filter import CandidateFilter
from .candidate_matcher import CandidateMatcher
from .llm_validator import LLMValidator
from .decision_engine import DecisionEngine


class VehicleCodeifier:
    """Simplified vehicle codification service using modular components."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)

        # Core processing components
        self.preprocessor = VehiclePreprocessor()
        self.extractor = VehicleExtractor()
        self.label_builder = VehicleLabelBuilder()
        self.cache = VehicleCatalogCache()

        # Modular components
        self.candidate_filter = CandidateFilter(self.engine, self.settings)
        self.candidate_matcher = CandidateMatcher(self.engine, self.cache, self.settings)
        self.decision_engine = DecisionEngine(self.settings)

        # Initialize OpenAI client for LLM validation
        self.openai_client = None
        if self.settings.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.settings.openai_api_key)

        self.llm_validator = LLMValidator(self.openai_client, self.settings.openai_model)

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
            extracted_fields = self._convert_to_extracted_fields(extracted_fields_with_confidence)

            # Step 3: Try high-confidence filtering first
            print(f"🔧 Step 3: Applying high-confidence filters directly...")
            pre_filtered_candidates, total_before_filtering, dynamic_filter_results = self.candidate_filter.find_candidates_with_high_confidence_filters(
                extracted_fields_with_confidence, year
            )

            candidates = []
            debug_info = None

            if pre_filtered_candidates:
                # Use pre-filtered candidates if we found any
                candidates = pre_filtered_candidates
                print(f"📊 Using {len(pre_filtered_candidates)} pre-filtered candidates directly")
            else:
                # Fallback to traditional search methods
                print(f"🔍 No high-confidence filtering results, using hybrid/fallback search...")

                # Step 4: Generate embedding for similarity search (using raw description)
                description = processed["description"]
                embedding = self.extractor.generate_embedding_safe(description)

                # Step 5: Find candidates using hybrid approach (cache + database)
                if embedding is not None:
                    print("🚀 Using embedding-based hybrid search...")
                    candidates, debug_info = self.candidate_matcher.find_candidates_hybrid(
                        description, extracted_fields, year, embedding
                    )
                    print(f"📊 Hybrid search returned {len(candidates)} candidates")
                else:
                    # Fallback to database search without embeddings
                    candidates, debug_info = self.candidate_matcher.find_candidates_fallback(extracted_fields, year)
                    print(f"📊 Fallback search returned {len(candidates)} candidates")

            # Step 6: LLM validation of candidates
            print(f"🔍 DEBUG: About to check LLM validation - OpenAI client: {self.openai_client is not None}, Candidates: {len(candidates)}")
            if self.openai_client and candidates:
                candidates = self.llm_validator.validate_candidates(
                    candidates, processed["description"], extracted_fields, year
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

            # Step 7: Apply decision thresholds
            print(f"🔍 DEBUG: About to make decision with {len(candidates)} candidates")
            if candidates:
                for i, c in enumerate(candidates[:3]):
                    print(f"   {i+1}. {c.marca} {c.submarca} (final_score: {c.final_score})")
            decision, confidence, suggested_cvegs = self.decision_engine.make_decision(candidates, extracted_fields)
            print(f"🔍 DEBUG: Decision made - decision: {decision}, confidence: {confidence}, suggested_cvegs: {suggested_cvegs}")

            # Step 8: Create enhanced response with review candidates
            top_candidates_for_review = self.decision_engine.create_review_candidates(candidates, decision)
            recommendation = self.decision_engine.get_recommendation(decision, confidence)

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

    def _convert_to_extracted_fields(self, extracted_fields_with_confidence) -> ExtractedFields:
        """Convert ExtractedFieldsWithConfidence to ExtractedFields for backward compatibility."""
        return ExtractedFields(
            marca=extracted_fields_with_confidence.marca.value if extracted_fields_with_confidence.marca.value else None,
            submarca=extracted_fields_with_confidence.submarca.value if extracted_fields_with_confidence.submarca.value else None,
            cvesegm=extracted_fields_with_confidence.cvesegm.value if extracted_fields_with_confidence.cvesegm.value else None,
            tipveh=extracted_fields_with_confidence.tipveh.value if extracted_fields_with_confidence.tipveh.value else None,
            descveh=extracted_fields_with_confidence.descveh
        )