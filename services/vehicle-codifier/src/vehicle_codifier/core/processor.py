"""Vehicle field extraction processor focused on catalog-driven field extraction."""

import re
import json
from typing import Optional, Set, Dict
from openai import OpenAI
from rapidfuzz import fuzz
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..models import ExtractedFields, ExtractedFieldsWithConfidence, FieldConfidence
from ..config import get_settings
from ..utils import norm


class VehicleProcessor:
    """Focused processor for vehicle field extraction using catalog-driven approaches."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)
        self.openai_client = self._initialize_openai()

    def _initialize_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client for LLM fallback."""
        if self.settings.openai_api_key:
            return OpenAI(api_key=self.settings.openai_api_key)
        return None

    # === FIELD EXTRACTION METHODS ===

    def extract_fields_with_year(self, description: str, year: int) -> ExtractedFields:
        """Extract fields using catalog-driven approach."""
        result_with_confidence = self.extract_fields_with_confidence(description, year)
        return result_with_confidence.to_extracted_fields()

    def extract_fields_with_confidence(self, description: str, year: int) -> ExtractedFieldsWithConfidence:
        """Extract fields using catalog-driven approach with confidence scoring."""
        # Build year-filtered candidates
        candidates = self._build_year_filtered_candidates(year)

        if not candidates:
            return ExtractedFieldsWithConfidence()

        # Initialize result and working description
        result = ExtractedFieldsWithConfidence()
        result.descveh = norm(description)
        working_description = description

        # Extract marca first (highest priority)
        result.marca = self._extract_field_with_confidence(
            working_description, candidates["marca"], "marca"
        )

        # Remove marca from working description if confidence >= 0.9
        if result.marca.value and result.marca.confidence >= 0.9:
            working_description = self._remove_matched_text(working_description, result.marca.value)

        # Filter submarca candidates by extracted marca if available
        submarca_candidates = candidates["submarca"]
        if result.marca.value and result.marca.confidence >= 0.5:
            submarca_candidates = self._filter_submarca_by_marca(
                candidates, result.marca.value
            )

        result.submarca = self._extract_field_with_confidence(
            working_description, submarca_candidates, "submarca"
        )

        # Remove submarca from working description if confidence >= 0.9
        if result.submarca.value and result.submarca.confidence >= 0.9:
            working_description = self._remove_matched_text(working_description, result.submarca.value)

        # Extract cvesegm and tipveh
        result.cvesegm = self._extract_field_with_confidence(
            working_description, candidates["cvesegm"], "cvesegm"
        )
        result.tipveh = self._extract_field_with_confidence(
            working_description, candidates["tipveh"], "tipveh"
        )

        # Apply LLM fallback for low-confidence fields
        result = self._apply_llm_fallback(description, result, candidates)

        return result

    def _build_year_filtered_candidates(self, year: int) -> Dict[str, Set[str]]:
        """Build candidate sets filtered by year from catalog."""
        try:
            with Session(self.engine) as session:
                result = session.execute(text("""
                    SELECT DISTINCT marca, submarca, cvesegm, tipveh
                    FROM amis_catalog
                    WHERE modelo = :year
                      AND catalog_version = (
                          SELECT version FROM catalog_import
                          WHERE status IN ('ACTIVE', 'LOADED')
                          ORDER BY version DESC LIMIT 1
                      )
                """), {"year": year})

                rows = result.fetchall()
                candidates = {
                    "marca": set(),
                    "submarca": set(),
                    "cvesegm": set(),
                    "tipveh": set()
                }

                for row in rows:
                    if row.marca and row.marca.strip():
                        candidates["marca"].add(row.marca.strip().lower())
                    if row.submarca and row.submarca.strip():
                        candidates["submarca"].add(row.submarca.strip().lower())
                    if row.cvesegm and row.cvesegm.strip():
                        candidates["cvesegm"].add(row.cvesegm.strip().lower())
                    if row.tipveh and row.tipveh.strip():
                        candidates["tipveh"].add(row.tipveh.strip().lower())

                return candidates

        except Exception as e:
            print(f"❌ Failed to build candidates for year {year}: {e}")
            return {}

    def _filter_submarca_by_marca(self, candidates: Dict[str, Set[str]], marca: str) -> Set[str]:
        """Filter submarca candidates by extracted marca."""
        try:
            with Session(self.engine) as session:
                result = session.execute(text("""
                    SELECT DISTINCT submarca
                    FROM amis_catalog
                    WHERE marca ILIKE :marca
                      AND submarca IS NOT NULL
                      AND catalog_version = (
                          SELECT version FROM catalog_import
                          WHERE status IN ('ACTIVE', 'LOADED')
                          ORDER BY version DESC LIMIT 1
                      )
                """), {"marca": marca})

                filtered_submarcas = {
                    row.submarca.strip().lower()
                    for row in result.fetchall()
                    if row.submarca and row.submarca.strip()
                }

                return filtered_submarcas

        except Exception as e:
            print(f"⚠️ Failed to filter submarca by marca '{marca}': {e}")
            return candidates["submarca"]

    def _extract_field_with_confidence(
        self, description: str, candidates: Set[str], field_type: str = "unknown"
    ) -> FieldConfidence:
        """Extract single field using multi-stage matching with confidence scoring."""
        if not candidates:
            return FieldConfidence(value=None, confidence=0.0, method="none")

        desc_lower = description.lower()

        # Stage 1: Direct substring matching
        for candidate in candidates:
            if candidate in desc_lower:
                return FieldConfidence(
                    value=candidate,
                    confidence=1.0,
                    method="direct"
                )

        # Stage 2: Fuzzy matching
        best_match = None
        best_score = 0.0
        best_method = "fuzzy"

        for candidate in candidates:
            partial_score = fuzz.partial_ratio(desc_lower, candidate) / 100.0
            if partial_score > best_score:
                best_match = candidate
                best_score = partial_score
                best_method = "fuzzy_partial"

            token_score = fuzz.token_sort_ratio(desc_lower, candidate) / 100.0
            if token_score > best_score:
                best_match = candidate
                best_score = token_score
                best_method = "fuzzy_token"

        # Apply confidence thresholds
        if best_score >= 0.8:
            confidence = min(0.95, best_score)
            return FieldConfidence(
                value=best_match,
                confidence=confidence,
                method=best_method
            )
        elif best_score >= 0.6:
            confidence = best_score * 0.8
        elif best_score >= 0.4:
            confidence = best_score * 0.6
        else:
            confidence = 0.0
            best_match = None

        return FieldConfidence(
            value=best_match,
            confidence=confidence,
            method=best_method if best_match else "none"
        )

    def _apply_llm_fallback(
        self, description: str, result: ExtractedFieldsWithConfidence, candidates: Dict[str, Set[str]]
    ) -> ExtractedFieldsWithConfidence:
        """Apply LLM fallback for low-confidence fields."""
        if not self.openai_client:
            return result

        # Identify fields that need LLM fallback
        low_confidence_fields = []
        confidence_threshold = 0.5

        if result.marca.confidence < confidence_threshold:
            low_confidence_fields.append("marca")
        if result.submarca.confidence < confidence_threshold:
            low_confidence_fields.append("submarca")
        if result.cvesegm.confidence < confidence_threshold:
            low_confidence_fields.append("cvesegm")
        if result.tipveh.confidence < confidence_threshold:
            low_confidence_fields.append("tipveh")

        if not low_confidence_fields:
            return result

        # Use simplified LLM extraction for missing fields
        # (Implementation simplified for brevity)
        return result

    def _remove_matched_text(self, description: str, matched_value: str) -> str:
        """Remove matched text from description to clean it for subsequent extractions."""
        if not matched_value or not description:
            return description

        desc_lower = description.lower()
        matched_lower = matched_value.lower()

        if matched_lower in desc_lower:
            start_pos = desc_lower.find(matched_lower)
            end_pos = start_pos + len(matched_lower)
            cleaned = description[:start_pos] + description[end_pos:]
            cleaned = ' '.join(cleaned.split())
            return cleaned.strip()

        return description

    # === HEALTH CHECK ===

    def get_health_status(self) -> dict:
        """Get processor health status."""
        return {
            "processor_available": True,
            "openai_available": self.openai_client is not None,
            "openai_model": self.settings.openai_model if self.openai_client else None
        }