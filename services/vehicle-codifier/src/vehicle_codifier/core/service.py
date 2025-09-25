"""Simplified vehicle codification service using unified processor."""

import time
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine
import openai

from ..config import get_settings
from ..models import VehicleInput, MatchResult, ExtractedFields, PostProcessorInput
from ..pipeline import VehiclePreprocessor, DecisionEngine, LLMReranker, filter_candidates_with_high_confidence, FieldExtractor
from ..pipeline.filtering import apply_progressive_fallback
from ..pipeline.fuzzy_matching import apply_fuzzy_matching
from ..search import VehicleCatalogCache, CandidateFilter, CandidateMatcher
from ..pipeline.embedding_scoring import build_query_label


class VehicleCodeifier:
    """Simplified vehicle codification service using unified processor."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)

        # Core components with separation of concerns
        self.field_extractor = FieldExtractor()  # Focused on field extraction only
        # Pipeline components
        self.preprocessor = VehiclePreprocessor()
        self.cache = VehicleCatalogCache()
        self.candidate_filter = CandidateFilter(self.engine, self.settings)
        self.candidate_matcher = CandidateMatcher(self.engine, self.cache, self.settings)
        self.decision_engine = DecisionEngine(self.settings)

        # Initialize OpenAI client for LLM finalizer
        self.openai_client = None
        if self.settings.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.settings.openai_api_key)

        # Import LLM finalizer and final selector
        from ..pipeline.llm_finalizer import finalize_candidates_with_llm, select_final_candidate
        self.llm_finalizer = finalize_candidates_with_llm
        self.final_selector = select_final_candidate

        # (CandidatePostProcessor removed)

    def match_vehicle(self, vehicle_input: VehicleInput) -> MatchResult:
        """Match a single vehicle against the CATVER catalog."""
        start_time = time.time()
        print("[DEBUG] match_vehicle: Starting vehicle match")
        print(f"[DEBUG] Input: modelo={vehicle_input.modelo}, description={vehicle_input.description}")

        try:
            # Step 1: Preprocess input (smart field detection and normalization)
            print("[DEBUG] Step 1: Preprocessing input")
            raw_input = {"modelo": vehicle_input.modelo, "description": vehicle_input.description}
            processed_batch = self.preprocessor.process(raw_input)
            processed = processed_batch["0"]  # Extract single row from batch result
            print(f"[DEBUG] Step 1: Preprocessing result: model_year={processed['model_year']}, description={processed['description']}")

            # Step 2: Extract CATVER fields from normalized description using unified processor
            print("[DEBUG] Step 2: Extracting fields with confidence")
            year = processed["model_year"]
            extracted_fields_with_confidence = self.field_extractor.extract_fields_with_confidence(processed["description"], year)
            print(f"[DEBUG] Step 2: Extracted fields: {extracted_fields_with_confidence}")
            if hasattr(extracted_fields_with_confidence, "marca"):
                print(f"[DEBUG] Step 2: Marca={extracted_fields_with_confidence.marca.value}, Confidence={extracted_fields_with_confidence.marca.confidence}")
                print(f"[DEBUG] Step 2: Submarca={extracted_fields_with_confidence.submarca.value}, Confidence={extracted_fields_with_confidence.submarca.confidence}")
                print(f"[DEBUG] Step 2: Tipveh={extracted_fields_with_confidence.tipveh.value}, Confidence={extracted_fields_with_confidence.tipveh.confidence}")

            # Step 3: Try high-confidence filtering first
            print("[DEBUG] Step 3: High-confidence candidate filtering")
            candidates, applied_filters = filter_candidates_with_high_confidence(
                extracted_fields_with_confidence, year, self.engine, self.settings
            )
            print(f"[DEBUG] Step 3: Candidates after filtering: {len(candidates)}")
            
            # Step 3b: Progressive fallback if no candidates found
            if len(candidates) == 0:
                print("[DEBUG] Step 3b: No candidates found, applying progressive fallback...")
                candidates, applied_filters = apply_progressive_fallback(
                    extracted_fields_with_confidence, year, self.engine, self.settings
                )
                print(f"[DEBUG] Step 3b: Candidates after fallback: {len(candidates)}")

            debug_info = None
            description = processed["description"]

            # Step 3b: Fuzzy matching after filtering
            print("[DEBUG] Step 3b: Fuzzy matching on filtered candidates")
            candidates = apply_fuzzy_matching(candidates, description)
            if candidates and hasattr(candidates[0], "fuzzy_score"):
                print(f"[DEBUG] Step 3b: Top candidate fuzzy_score: {candidates[0].fuzzy_score}")

            # Step 4: Embedding-based candidate scoring after filtering
            print("[DEBUG] Step 4: Embedding-based candidate scoring")
            from ..pipeline.embedding_scoring import score_candidates_with_embedding
            candidates = score_candidates_with_embedding(
                candidates, description
            )
            print(f"[DEBUG] Step 4: Candidates after embedding scoring: {len(candidates)}")
            if candidates and hasattr(candidates[0], "similarity_score"):
                print(f"[DEBUG] Step 4: Top candidate similarity_score: {candidates[0].similarity_score}")
            debug_info = {"embedding_scoring_applied": True}

            # Step 5: Mix all scores into final_score (no LLM weight, BEFORE LLM finalizer)
            print("[DEBUG] Step 5: Mixing all scores into final_score (no LLM weight, before LLM finalizer)")
            def mix_candidate_scores(candidate):
                # Adjusted weights: filter, fuzzy, embedding (sum to 1.0)
                w_filter = 0.4
                w_fuzzy = 0.3
                w_embed = 0.3
                return (
                    w_filter * candidate.final_score +
                    w_fuzzy * candidate.fuzzy_score +
                    w_embed * candidate.similarity_score
                )
            for candidate in candidates:
                candidate.final_score = mix_candidate_scores(candidate)
            if candidates:
                print(f"[DEBUG] Step 5: Top candidate final_score: {candidates[0].final_score}")

            # Step 6: LLM finalizer on top 10 candidates by mixed score
            print("[DEBUG] Step 6: LLM finalizer on top 10 candidates by mixed score")
            from ..pipeline.llm_finalizer import finalize_candidates_with_llm
            extracted_fields = extracted_fields_with_confidence.to_extracted_fields()
            llm_results, llm_notice = finalize_candidates_with_llm(
                candidates, description, extracted_fields, year, self.openai_client, self.settings.openai_model
            )
            if llm_results:
                print(f"[DEBUG] Step 6: LLM finalizer returned {len(llm_results)} candidates")
                candidates = []
                for idx, res in enumerate(llm_results):
                    c = res["candidate"]
                    conf = res["llm_confidence"]
                    c.llm_score = conf if conf is not None else 0.0
                    print(f"[DEBUG]   Candidate {idx+1}: {c.marca} {c.submarca} {c.modelo} (llm_score: {c.llm_score})")
                    candidates.append(c)
            else:
                print("[DEBUG] Step 6: No candidates after LLM finalizer (empty input or LLM returned empty)")
                # Fallback: use top 3 by final_score, llm_score=0.0
                candidates = sorted(candidates, key=lambda c: c.final_score, reverse=True)[:3]
                for c in candidates:
                    c.llm_score = 0.0
            if llm_notice:
                print(f"[DEBUG] LLM finalizer notice: {llm_notice}")

            # Step 7: GPT-5 Final Selector (determines suggested CVEGS, keeps all candidates)
            print("[DEBUG] Step 7: GPT-5 Final Selector")
            gpt5_suggested_cvegs = None
            if self.settings.enable_gpt5_final_selection and candidates:
                selected_candidate, notice = self.final_selector(
                    candidates, description, year, self.openai_client, self.settings.gpt5_model
                )
                if selected_candidate:
                    # Mark the selected candidate but keep all candidates
                    selected_candidate.gpt5_selected = True
                    gpt5_suggested_cvegs = selected_candidate.cvegs
                    print(f"[DEBUG] GPT-5 selected: {selected_candidate.marca} {selected_candidate.submarca} (CVEGS: {gpt5_suggested_cvegs})")
                if notice:
                    print(f"[DEBUG] {notice}")
            else:
                print("[DEBUG] GPT-5 selection skipped")

            # Step 8: Apply decision engine (with GPT-5 suggestion)
            print("[DEBUG] Step 8: Applying decision engine")
            decision, confidence, suggested_cvegs = self.decision_engine.make_decision(candidates, extracted_fields)
            
            # Override suggested_cvegs with GPT-5 selection if available
            if gpt5_suggested_cvegs is not None:
                suggested_cvegs = gpt5_suggested_cvegs
                print(f"[DEBUG] Using GPT-5 suggested CVEGS: {suggested_cvegs}")
            
            print(f"[DEBUG] Step 8: Decision={decision}, Confidence={confidence}, Suggested CVEGS={suggested_cvegs}")

            # Add processing time
            processing_time = (time.time() - start_time) * 1000

            # Build query label using embedding service
            query_label = None
            if extracted_fields:
                query_label = build_query_label(year, extracted_fields)

            # Create MatchResult object
            from ..models import MatchResult
            result = MatchResult(
                success=(decision != "no_match"),
                decision=decision,
                confidence=confidence,
                suggested_cvegs=suggested_cvegs,
                candidates=candidates,
                extracted_fields=extracted_fields,
                processing_time_ms=processing_time,
                query_label=query_label
            )

            # Add debug information
            # Note: pre_filtered_candidates is not defined in this scope, so skip those debug lines
            if debug_info:
                result.debug_info = debug_info.copy()

            print("[DEBUG] match_vehicle: Finished vehicle match")
            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            print(f"[ERROR] match_vehicle: Exception occurred: {e}")
            from ..models import MatchResult
            return MatchResult(
                success=False,
                decision="no_match",
                confidence=0.0,
                processing_time_ms=processing_time,
                query_label=f"Error: {str(e)}"
            )

    def _convert_to_extracted_fields(self, fields_with_confidence: Any) -> ExtractedFields:
        """Convert ExtractedFieldsWithConfidence to ExtractedFields."""
        return ExtractedFields(
            marca=fields_with_confidence.marca.value if fields_with_confidence.marca.value else None,
            submarca=fields_with_confidence.submarca.value if fields_with_confidence.submarca.value else None,
            descveh=fields_with_confidence.descveh,
            tipveh=fields_with_confidence.tipveh.value if fields_with_confidence.tipveh.value else None
        )


    def match_vehicles_batch(self, vehicles: List[VehicleInput]) -> List[MatchResult]:
        """Match multiple vehicles against the CATVER catalog."""
        results = []
        for vehicle in vehicles:
            try:
                result = self.match_vehicle(vehicle)
                results.append(result)
            except Exception as e:
                print(f"❌ Batch processing failed for vehicle: {e}")
                results.append(MatchResult(
                    success=False,
                    decision="no_match",
                    confidence=0.0,
                    processing_time_ms=0.0,
                    query_label=f"Error: {str(e)}"
                ))
        return results
