"""High-confidence candidate filtering pipeline component."""

from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Candidate, ExtractedFieldsWithConfidence


def filter_candidates_with_high_confidence(
    extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
    year: int,
    engine,
    settings,
    apply_filter: Optional[List[str]] = None
) -> Tuple[List[Candidate], List[Dict]]:
    """Filter candidates using high-confidence extracted fields (Pipeline Step 3).

    Args:
        extracted_fields_with_confidence: Fields with confidence scores
        year: Vehicle year
        engine: Database engine
        settings: Configuration settings
        apply_filter: Optional list of filters to apply in order (e.g., ["marca", "submarca"]).
                      If None, applies the default filter sequence.

    Returns:
        Tuple of (filtered_candidates, applied_filters)
    """
    # Build WHERE conditions based on high confidence scores (≥0.9)
    where_conditions = [
        "modelo = :year",
        "catalog_version = (SELECT version FROM catalog_import WHERE status IN ('ACTIVE', 'LOADED') ORDER BY version DESC LIMIT 1)"
    ]
    sql_params = {"year": year}
    applied_filters = []

    # Check each field for high confidence and add to SQL filter
    confidence_threshold = settings.high_confidence_threshold

    # Apply high-confidence filters
    if apply_filter:
        filter_map = {
            "marca": _apply_marca_filter,
            "tipveh": _apply_tipveh_filter,
            "submarca": _apply_submarca_filter,
        }
        for name in apply_filter:
            func = filter_map.get(name)
            if func:
                func(
                    extracted_fields_with_confidence, confidence_threshold,
                    where_conditions, sql_params, applied_filters
                )
    else:
        # Default filters: marca, tipveh, submarca (removed cvesegm)
        _apply_marca_filter(
            extracted_fields_with_confidence, confidence_threshold,
            where_conditions, sql_params, applied_filters
        )

        _apply_tipveh_filter(
            extracted_fields_with_confidence, confidence_threshold,
            where_conditions, sql_params, applied_filters
        )

        _apply_submarca_filter(
            extracted_fields_with_confidence, confidence_threshold,
            where_conditions, sql_params, applied_filters
        )

    # Execute filtered query
    candidates = _execute_filtered_query(where_conditions, sql_params, applied_filters, engine)

    print(f"🎯 High-confidence filtering: {len(candidates)} candidates after filtering")

    return candidates, applied_filters


def apply_progressive_fallback(
    extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
    year: int,
    engine,
    settings
) -> Tuple[List[Candidate], List[Dict]]:
    """Apply progressive fallback when initial filtering returns 0 candidates.
    
    Fallback sequence:
    1. All 3 filters (marca, tipveh, submarca) → if 0 candidates
    2. Remove submarca (marca + tipveh) → if still 0 candidates  
    3. Remove tipveh (marca only) → if still 0 candidates
    4. Remove marca, try tipveh only → if still 0 candidates
    5. No field filters (year + catalog only)
    """
    
    fallback_sequences = [
        (["marca", "tipveh"], "Removing submarca (least priority)"),
        (["marca"], "Removing tipveh (keeping highest priority marca)"), 
        (["tipveh"], "Trying tipveh only (removing marca)"),
        ([], "No field filters (year + catalog only)")
    ]
    
    for retry_filters, reason in fallback_sequences:
        print(f"[DEBUG] Fallback attempt: {reason}")
        print(f"[DEBUG] Retry filters: {retry_filters}")
        
        candidates, applied_filters = filter_candidates_with_high_confidence(
            extracted_fields_with_confidence, year, engine, settings, 
            apply_filter=retry_filters if retry_filters else None
        )
        
        if len(candidates) > 0:
            print(f"[DEBUG] ✅ Fallback successful: {len(candidates)} candidates found with filters {retry_filters}")
            return candidates, applied_filters
        else:
            print(f"[DEBUG] ❌ Fallback failed: 0 candidates with filters {retry_filters}")
    
    # If we get here, even the most basic filtering failed
    print("[DEBUG] 🚨 All fallback attempts failed - returning empty results")
    return [], []


def _apply_marca_filter(
    extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
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
    extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
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




def _apply_submarca_filter(
    extracted_fields_with_confidence: ExtractedFieldsWithConfidence,
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
    where_conditions: List[str], sql_params: Dict[str, Any], applied_filters: List[Dict], engine
) -> List[Candidate]:
    """Execute the filtered SQL query and return candidates."""
    candidates = []

    try:
        with Session(engine) as session:
            sql = f"""
                SELECT cvegs, marca, submarca, modelo, descveh, tipveh, embedding
                FROM amis_catalog
                WHERE {' AND '.join(where_conditions)}
            """

            result = session.execute(text(sql), sql_params)

            for row in result:
                # Calculate confidence score based on number of high-confidence filters matched
                num_filters_applied = len(applied_filters)
                if num_filters_applied >= 2:
                    confidence_score = 1   # High confidence with 2 filters
                elif num_filters_applied == 1:
                    confidence_score = 0.95   # Medium confidence with 1 filter
                else:
                    confidence_score = 0.8   # Lower confidence with no high-confidence filters

                # Parse embedding if present
                embedding = None
                if hasattr(row, "embedding") and row.embedding is not None:
                    try:
                        embedding_str = row.embedding.strip('[]')
                        embedding = [float(x.strip()) for x in embedding_str.split(',')]
                    except Exception as e:
                        print(f"[DEBUG] Could not parse embedding for cvegs={row.cvegs}: {e}")

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
                    tipveh=row.tipveh,
                    embedding=embedding
                )
                candidates.append(candidate)

    except Exception as e:
        print(f"⚠️ Error executing filtered query: {e}")
        return []

    return candidates
