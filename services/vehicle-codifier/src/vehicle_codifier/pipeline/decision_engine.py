"""Decision engine for vehicle matching results."""

from typing import List, Tuple, Optional

from ..models import Candidate, ExtractedFields, ReviewCandidate
from ..config import Settings


class DecisionEngine:
    """Handles decision-making logic based on confidence thresholds."""

    def __init__(self, settings: Settings):
        """Initialize the decision engine with settings."""
        self.settings = settings

    def make_decision(self, candidates: List[Candidate], fields: ExtractedFields) -> Tuple[str, float, Optional[int]]:
        """Apply dynamic decision thresholds based on vehicle type."""
        if not candidates:
            return "no_match", 0.0, None

        best_candidate = candidates[0]
        confidence = best_candidate.llm_score

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

        vehicle_type_clean = vehicle_type.lower().strip()

        # Map vehicle types to threshold categories
        if vehicle_type_clean in ["auto", "sedan", "hatchback", "coupe"]:
            return self.settings.thresholds_by_type["auto"]
        elif vehicle_type_clean in ["camioneta", "pickup", "truck", "tracto", "tracto camion"]:
            return self.settings.thresholds_by_type["camioneta"]
        elif vehicle_type_clean in ["motocicleta", "motorcycle", "moto", "scooter"]:
            return self.settings.thresholds_by_type["motocicleta"]
        else:
            return self.settings.thresholds_by_type["default"]

    def create_review_candidates(self, candidates: List[Candidate], decision: str) -> List[ReviewCandidate]:
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
                confidence=candidate.llm_score,
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
        elif confidence >= 0.5:
            return "low"
        else:
            return "very_low"

    def get_recommendation(self, decision: str, confidence: float) -> str:
        """Get recommendation text based on decision and confidence."""
        if decision == "auto_accept":
            return f"High confidence match (confidence: {confidence:.2f}). Recommended for automatic acceptance."
        elif decision == "needs_review":
            return f"Medium confidence match (confidence: {confidence:.2f}). Requires manual review."
        else:
            return f"No confident match found (confidence: {confidence:.2f}). Consider manual search or additional information."
