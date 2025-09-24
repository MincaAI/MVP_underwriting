"""Dynamic candidate filtering based on extracted field confidence scores."""

from typing import List, Tuple, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Candidate, ExtractedFieldsWithConfidence
from ..config import Settings


class CandidateFilter:
    """Handles dynamic filtering of candidates based on confidence scores."""

    def __init__(self, engine, settings: Settings):
        """Initialize the candidate filter with database engine and settings."""
        self.engine = engine
        self.settings = settings

    def find_candidates_with_high_confidence_filters(
        self, extracted_fields_with_confidence: ExtractedFieldsWithConfidence, year: int
    ) -> Tuple[List[Candidate], int, List[Dict]]:
        """Find candidates using high-confidence filters (≥0.9) directly in SQL."""

        # Build WHERE conditions based on high confidence scores (≥0.9)
        where_conditions = [
            "modelo = :year",
            "catalog_version = (SELECT version FROM catalog_import WHERE status IN ('ACTIVE', 'LOADED') ORDER BY version DESC LIMIT 1)"
        ]
        sql_params = {"year": year}
        applied_filters = []

        # Check each field for high confidence and add to SQL filter
        confidence_threshold = self.settings.high_confidence_threshold

        # Get total count before filtering (for reporting)
        total_before_filter = self._get_total_candidates_for_year(year)

        # Apply high-confidence filters
        self._apply_marca_filter(
            extracted_fields_with_confidence, confidence_threshold,
            where_conditions, sql_params, applied_filters
        )

        self._apply_tipveh_filter(
            extracted_fields_with_confidence, confidence_threshold,
            where_conditions, sql_params, applied_filters
        )

        self._apply_cvesegm_filter(
            extracted_fields_with_confidence, confidence_threshold,
            where_conditions, sql_params, applied_filters
        )

        self._apply_submarca_filter(
            extracted_fields_with_confidence, confidence_threshold,
            where_conditions, sql_params, applied_filters
        )

        # Execute filtered query
        candidates = self._execute_filtered_query(where_conditions, sql_params, applied_filters)

        print(f"🎯 High-confidence filtering: {total_before_filter} → {len(candidates)} candidates")
        if len(candidates) < total_before_filter:
            print(f"🎯 Direct filtering result: {len(candidates)} candidates remain ({len(candidates)/total_before_filter*100:.2f}% of original)")

        return candidates, total_before_filter, applied_filters

    def _get_total_candidates_for_year(self, year: int) -> int:
        """Get total count of candidates for the given year."""
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
                return total_result.fetchone().total
        except Exception as e:
            print(f"⚠️ Error counting total candidates: {e}")
            return 0

    def _apply_marca_filter(
        self, extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
        confidence_threshold: float, where_conditions: List[str],
        sql_params: Dict[str, Any], applied_filters: List[Dict]
    ) -> None:
        """Apply marca filter if confidence is high enough."""
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

    def _apply_tipveh_filter(
        self, extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
        confidence_threshold: float, where_conditions: List[str],
        sql_params: Dict[str, Any], applied_filters: List[Dict]
    ) -> None:
        """Apply tipveh filter if confidence is high enough."""
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

    def _apply_cvesegm_filter(
        self, extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
        confidence_threshold: float, where_conditions: List[str],
        sql_params: Dict[str, Any], applied_filters: List[Dict]
    ) -> None:
        """Apply cvesegm filter if confidence is high enough."""
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

    def _apply_submarca_filter(
        self, extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
        confidence_threshold: float, where_conditions: List[str],
        sql_params: Dict[str, Any], applied_filters: List[Dict]
    ) -> None:
        """Apply submarca filter if confidence is high enough."""
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

    def _execute_filtered_query(
        self, where_conditions: List[str], sql_params: Dict[str, Any], applied_filters: List[Dict]
    ) -> List[Candidate]:
        """Execute the filtered SQL query and return candidates."""
        candidates = []

        try:
            with Session(self.engine) as session:
                sql = f"""
                    SELECT cvegs, marca, submarca, modelo, descveh, cvesegm, tipveh
                    FROM amis_catalog
                    WHERE {' AND '.join(where_conditions)}
                """

                result = session.execute(text(sql), sql_params)

                for row in result:
                    # Calculate confidence score based on number of high-confidence filters matched
                    num_filters_applied = len(applied_filters)
                    if num_filters_applied >= 3:
                        confidence_score = 0.95  # Very high confidence with 3+ filters
                    elif num_filters_applied == 2:
                        confidence_score = 0.85  # High confidence with 2 filters
                    elif num_filters_applied == 1:
                        confidence_score = 0.75  # Medium confidence with 1 filter
                    else:
                        confidence_score = 0.65  # Lower confidence with no high-confidence filters

                    candidate = Candidate(
                        cvegs=row.cvegs,
                        marca=row.marca,
                        submarca=row.submarca,
                        modelo=row.modelo,
                        descveh=row.descveh,
                        label=None,  # Labels no longer used
                        similarity_score=0.0,  # Not applicable for direct filtering
                        fuzzy_score=0.0,      # Not applicable for direct filtering
                        final_score=confidence_score,
                        cvesegm=row.cvesegm,
                        tipveh=row.tipveh
                    )
                    candidates.append(candidate)

        except Exception as e:
            print(f"⚠️ Error executing filtered query: {e}")
            return []

        return candidates
