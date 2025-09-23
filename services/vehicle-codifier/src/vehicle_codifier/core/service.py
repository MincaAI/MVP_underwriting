"""Simplified vehicle codification service using unified processor."""

import time
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine
import openai

from ..config import get_settings
from ..models import VehicleInput, MatchResult, ExtractedFields, PostProcessorInput
from .processor import VehicleProcessor
from ..pipeline import VehiclePreprocessor, DecisionEngine, LLMReranker, filter_candidates_with_high_confidence
from ..pipeline.fuzzy_matching import apply_fuzzy_matching
from ..search import VehicleCatalogCache, CandidateFilter, CandidateMatcher
from ..pipeline.embedding_scoring import build_query_label


class VehicleCodeifier:
    """Simplified vehicle codification service using unified processor."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)

        # Core components with separation of concerns
        self.processor = VehicleProcessor()  # Focused on field extraction only
        # Pipeline components
        self.preprocessor = VehiclePreprocessor()
        self.cache = VehicleCatalogCache()
        self.candidate_filter = CandidateFilter(self.engine, self.settings)
        self.candidate_matcher = CandidateMatcher(self.engine, self.cache, self.settings)
        self.decision_engine = DecisionEngine(self.settings)

        # Initialize OpenAI client for LLM reranking
        self.openai_client = None
        if self.settings.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.settings.openai_api_key)

        self.llm_reranker = LLMReranker(self.openai_client, self.settings.openai_model)

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
            extracted_fields_with_confidence = self.processor.extract_fields_with_confidence(processed["description"], year)
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
            if candidates:
                print(f"[DEBUG] Step 3: First candidate: {candidates[0]}")

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

            # Step 4b: LLM reranker on top 20 embedded candidates
            print("[DEBUG] Step 4b: LLM reranking top 20 embedded candidates")
            from ..pipeline.llm_reranker import LLMReranker
            extracted_fields = extracted_fields_with_confidence.to_extracted_fields()
            reranked_candidates = LLMReranker.rerank_top_candidates(
                candidates, description, extracted_fields, year, self.llm_reranker
            )
            if reranked_candidates:
                candidates = reranked_candidates
                print(f"[DEBUG] Step 4b: Candidates after LLM reranking: {len(candidates)}")
                print(f"[DEBUG] Step 4b: Top candidate after reranking: {candidates[0]}")
            else:
                print("[DEBUG] Step 4b: No candidates after LLM reranking (empty input or reranker returned empty)")

            # Step 5: Mix all scores into final_score
            print("[DEBUG] Step 5: Mixing all scores into final_score")
            def mix_candidate_scores(candidate):
                # Example weights: adjust as needed for your use case
                w_filter = 0.25
                w_fuzzy = 0.2
                w_embed = 0.25
                w_llm = 0.3
                return (
                    w_filter * candidate.final_score +
                    w_fuzzy * candidate.fuzzy_score +
                    w_embed * candidate.similarity_score +
                    w_llm * candidate.llm_score
                )
            for candidate in candidates:
                candidate.final_score = mix_candidate_scores(candidate)
            if candidates:
                print(f"[DEBUG] Step 5: Top candidate final_score: {candidates[0].final_score}")

            # Step 6: Apply decision engine
            print("[DEBUG] Step 6: Applying decision engine")
            decision, confidence, suggested_cvegs = self.decision_engine.make_decision(candidates, extracted_fields)
            print(f"[DEBUG] Step 6: Decision={decision}, Confidence={confidence}, Suggested CVEGS={suggested_cvegs}")

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
            cvesegm=fields_with_confidence.cvesegm.value if fields_with_confidence.cvesegm.value else None,
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
