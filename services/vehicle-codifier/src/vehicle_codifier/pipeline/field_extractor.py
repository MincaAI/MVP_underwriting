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


class FieldExtractor:
    """Focused extractor for vehicle field extraction using catalog-driven approaches."""

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

        # Filter submarca candidates by extracted marca ONLY if marca has PERFECT confidence
        submarca_candidates = candidates["submarca"]
        print(f"[DEBUG] Initial submarca candidates ({len(submarca_candidates)} total): {sorted(list(submarca_candidates))}")
        
        if result.marca.value and result.marca.confidence >= 1.0:
            # Perfect marca confidence → filter submarca by marca relationship
            submarca_candidates = self._filter_submarca_by_marca(
                candidates, result.marca.value
            )
            print(f"[DEBUG] ✅ PERFECT marca confidence ({result.marca.confidence:.2f}) → Filtered submarca by marca '{result.marca.value}'")
            print(f"[DEBUG] Filtered submarca candidates ({len(submarca_candidates)} total): {sorted(list(submarca_candidates))}")
        else:
            # Low/uncertain marca confidence → keep ALL submarcas for this model year
            if result.marca.value:
                print(f"[DEBUG] ⚠️ LOW marca confidence ({result.marca.confidence:.2f}) for '{result.marca.value}' → Using ALL submarcas for model year")
            else:
                print(f"[DEBUG] ❌ NO marca extracted → Using ALL submarcas for model year")
            print(f"[DEBUG] Using all submarca candidates ({len(submarca_candidates)} total): {sorted(list(submarca_candidates))}")

        result.submarca = self._extract_field_with_confidence(
            working_description, submarca_candidates, "submarca"
        )

        # Remove submarca from working description if confidence >= 0.9
        if result.submarca.value and result.submarca.confidence >= 0.9:
            working_description = self._remove_matched_text(working_description, result.submarca.value)

        # Extract tipveh
        result.tipveh = self._extract_field_with_confidence(
            working_description, candidates["tipveh"], "tipveh"
        )

        # Apply LLM fallback for low-confidence fields
        result = self._apply_llm_fallback(description, result, candidates, year)

        return result

    def _build_year_filtered_candidates(self, year: int) -> Dict[str, Set[str]]:
        """Build candidate sets filtered by year from catalog."""
        try:
            with Session(self.engine) as session:
                result = session.execute(text("""
                    SELECT DISTINCT marca, submarca, tipveh
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
                    "tipveh": set()
                }

                for row in rows:
                    if row.marca and row.marca.strip():
                        candidates["marca"].add(row.marca.strip().lower())
                    if row.submarca and row.submarca.strip():
                        candidates["submarca"].add(row.submarca.strip().lower())
                    if row.tipveh and row.tipveh.strip():
                        candidates["tipveh"].add(row.tipveh.strip().lower())

                return candidates

        except Exception as e:
            print(f"❌ Failed to build candidates for year {year}: {e}")
            return {}

    def _get_candidates(self, year: int) -> Dict[str, Dict]:
        """Get candidates showing marca->submarca->tipveh relationships."""
        try:
            with Session(self.engine) as session:
                # Get all combinations with frequencies
                result = session.execute(text("""
                    SELECT marca, submarca, tipveh, COUNT(*) as frequency
                    FROM amis_catalog
                    WHERE modelo = :year
                      AND marca IS NOT NULL
                      AND catalog_version = (
                          SELECT version FROM catalog_import
                          WHERE status IN ('ACTIVE', 'LOADED')
                          ORDER BY version DESC LIMIT 1
                      )
                    GROUP BY marca, submarca, tipveh
                    ORDER BY marca ASC, frequency DESC
                """), {"year": year})

                hierarchical_data = {}
                
                for row in result.fetchall():
                    marca = row.marca.strip().lower() if row.marca else None
                    submarca = row.submarca.strip().lower() if row.submarca else None
                    tipveh = row.tipveh.strip().lower() if row.tipveh else None
                    frequency = row.frequency
                    
                    if not marca:
                        continue
                    
                    # Initialize marca if not exists
                    if marca not in hierarchical_data:
                        hierarchical_data[marca] = {
                            "total_frequency": 0,
                            "submarcas": {},
                            "tipvehs": set()
                        }
                    
                    # Update total frequency for marca
                    hierarchical_data[marca]["total_frequency"] += frequency
                    
                    # Add submarca if exists
                    if submarca:
                        if submarca not in hierarchical_data[marca]["submarcas"]:
                            hierarchical_data[marca]["submarcas"][submarca] = 0
                        hierarchical_data[marca]["submarcas"][submarca] += frequency
                    
                    # Add tipveh if exists
                    if tipveh:
                        hierarchical_data[marca]["tipvehs"].add(tipveh)

                return hierarchical_data

        except Exception as e:
            print(f"❌ Failed to get candidates for year {year}: {e}")
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
            print(f"[DEBUG] {field_type}: No candidates available")
            return FieldConfidence(value=None, confidence=0.0, method="none")

        desc_lower = description.lower()
        
        print(f"[DEBUG] ===== {field_type.upper()} EXTRACTION =====")
        print(f"[DEBUG] Description: '{desc_lower}'")
        print(f"[DEBUG] Candidates ({len(candidates)} total): {sorted(list(candidates))}")

        # Stage 1: Direct substring matching with longest-first strategy
        print(f"[DEBUG] Stage 1: Direct substring matching")
        
        # Sort candidates by length (longest first) to avoid shorter matches interfering
        sorted_candidates = sorted(candidates, key=len, reverse=True)
        print(f"[DEBUG] Sorted candidates (longest first): {sorted_candidates}")
        
        for candidate in sorted_candidates:
            print(f"[DEBUG] Testing candidate: '{candidate}' (length: {len(candidate)})")
            if candidate in desc_lower:
                print(f"[DEBUG] ✅ DIRECT MATCH FOUND: '{candidate}' found in '{desc_lower}'")
                return FieldConfidence(
                    value=candidate,
                    confidence=1.0,
                    method="direct"
                )
            else:
                print(f"[DEBUG] ❌ No direct match: '{candidate}' not found in '{desc_lower}'")
        
        print(f"[DEBUG] Stage 1 complete: No direct substring matches found")

        # Stage 2: Fuzzy matching
        print(f"[DEBUG] Stage 2: Fuzzy matching")
        best_match = None
        best_score = 0.0
        best_method = "fuzzy"

        for candidate in candidates:
            partial_score = fuzz.partial_ratio(desc_lower, candidate) / 100.0
            token_score = fuzz.token_sort_ratio(desc_lower, candidate) / 100.0
            
            print(f"[DEBUG] Fuzzy scores for '{candidate}': partial={partial_score:.3f}, token={token_score:.3f}")
            
            if partial_score > best_score:
                best_match = candidate
                best_score = partial_score
                best_method = "fuzzy_partial"
                print(f"[DEBUG] New best partial match: '{candidate}' (score: {partial_score:.3f})")

            if token_score > best_score:
                best_match = candidate
                best_score = token_score
                best_method = "fuzzy_token"
                print(f"[DEBUG] New best token match: '{candidate}' (score: {token_score:.3f})")

        print(f"[DEBUG] Best fuzzy match: '{best_match}' (score: {best_score:.3f}, method: {best_method})")

        # Apply confidence thresholds
        if best_score >= 0.8:
            confidence = min(0.95, best_score)
            print(f"[DEBUG] ✅ HIGH CONFIDENCE FUZZY MATCH: '{best_match}' (confidence: {confidence:.3f})")
            return FieldConfidence(
                value=best_match,
                confidence=confidence,
                method=best_method
            )
        elif best_score >= 0.6:
            confidence = best_score * 0.8
            print(f"[DEBUG] ⚠️ MEDIUM CONFIDENCE FUZZY MATCH: '{best_match}' (confidence: {confidence:.3f})")
        elif best_score >= 0.4:
            confidence = best_score * 0.6
            print(f"[DEBUG] ⚠️ LOW CONFIDENCE FUZZY MATCH: '{best_match}' (confidence: {confidence:.3f})")
        else:
            confidence = 0.0
            best_match = None
            print(f"[DEBUG] ❌ NO ACCEPTABLE FUZZY MATCH: All scores below threshold")

        final_result = FieldConfidence(
            value=best_match,
            confidence=confidence,
            method=best_method if best_match else "none"
        )
        print(f"[DEBUG] Final {field_type} result: value='{final_result.value}', confidence={final_result.confidence:.3f}, method={final_result.method}")
        print(f"[DEBUG] ===== END {field_type.upper()} EXTRACTION =====")
        
        return final_result

    def _apply_llm_fallback(
        self, description: str, result: ExtractedFieldsWithConfidence, candidates: Dict[str, Set[str]], year: int = None
    ) -> ExtractedFieldsWithConfidence:
        """Apply LLM fallback when overall extraction quality is poor."""
        if not self.openai_client:
            return result

        # Check if LLM fallback should be triggered based on overall quality
        should_trigger = self._should_trigger_llm_fallback(result)
        
        if not should_trigger:
            return result

        print("[DEBUG] LLM Fallback: Triggering due to poor overall extraction quality")
        
        # Use LLM for complete re-extraction of all fields
        try:
            llm_result = self._extract_with_llm(description, year if year else 2023)
            if llm_result:
                print("[DEBUG] LLM Fallback: Successfully re-extracted fields")
                return llm_result
            else:
                print("[DEBUG] LLM Fallback: Failed to extract fields, using original result")
                return result
        except Exception as e:
            print(f"[ERROR] LLM Fallback: Exception occurred: {e}")
            return result

    def _should_trigger_llm_fallback(self, result: ExtractedFieldsWithConfidence) -> bool:
        """Determine if LLM fallback should be triggered based on overall extraction quality."""
        # Trigger conditions:
        # 1. No high-confidence fields (all fields < 0.8)
        # 2. Critical fields missing (both marca AND submarca < 0.5)
        # 3. Overall extraction quality poor (average confidence < 0.6)
        
        confidences = [
            result.marca.confidence,
            result.submarca.confidence,
            result.tipveh.confidence
        ]
        
        # Check if no high-confidence fields
        high_confidence_threshold = 0.8
        has_high_confidence = any(conf >= high_confidence_threshold for conf in confidences)
        
        # Check if critical fields are missing
        critical_threshold = 0.5
        critical_fields_missing = (
            result.marca.confidence < critical_threshold and 
            result.submarca.confidence < critical_threshold
        )
        
        # Check overall quality
        avg_confidence = sum(confidences) / len(confidences)
        overall_quality_poor = avg_confidence < 0.6
        
        # Trigger if any condition is met
        should_trigger = not has_high_confidence or critical_fields_missing or overall_quality_poor
        
        if should_trigger:
            print(f"[DEBUG] LLM Fallback trigger analysis:")
            print(f"  - Has high confidence field: {has_high_confidence}")
            print(f"  - Critical fields missing: {critical_fields_missing}")
            print(f"  - Average confidence: {avg_confidence:.2f} (poor: {overall_quality_poor})")
            print(f"  - Individual confidences: marca={result.marca.confidence:.2f}, submarca={result.submarca.confidence:.2f}, tipveh={result.tipveh.confidence:.2f}")
        
        return should_trigger

    def _extract_with_llm(
        self, description: str, year: int
    ) -> Optional[ExtractedFieldsWithConfidence]:
        """Extract all fields using LLM with catalog context."""
        try:
            # Get candidates showing relationships
            candidates = self._get_candidates(year)
            
            # Prepare candidate context for LLM
            candidate_context = self._format_candidates(candidates, year)
            
            # Create structured prompt
            prompt = self._create_prompt(description, candidate_context)
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a vehicle field extraction expert. Extract vehicle information accurately from descriptions using the provided catalog options with hierarchical relationships."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse LLM response
            llm_output = response.choices[0].message.content
            return self._parse_llm_response(llm_output, description)
            
        except Exception as e:
            print(f"[ERROR] LLM extraction failed: {e}")
            return None

    def _format_candidates(self, hierarchical_data: Dict[str, Dict], year: int) -> str:
        """Format candidates showing marca->submarca->tipveh relationships."""
        if not hierarchical_data:
            return "No catalog data available for the specified year."
        
        context_parts = [f"VEHICLE OPTIONS for year {year}:\n"]
        
        # Sort marcas by total frequency (most popular first)
        sorted_marcas = sorted(
            hierarchical_data.items(),
            key=lambda x: x[1]["total_frequency"],
            reverse=True
        )
        
        for marca, marca_data in sorted_marcas:
            total_freq = marca_data["total_frequency"]
            context_parts.append(f"{marca.upper()} ({total_freq} total catalog entries):")
            
            # Format submarcas for this marca
            if marca_data["submarcas"]:
                # Sort submarcas by frequency
                sorted_submarcas = sorted(
                    marca_data["submarcas"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                
                submarca_list = []
                for submarca, freq in sorted_submarcas:
                    submarca_list.append(f"{submarca} ({freq} entries)")
                
                context_parts.append(f"  ├─ Submarcas: {', '.join(submarca_list)}")
            
            # Format tipvehs for this marca
            if marca_data["tipvehs"]:
                tipveh_list = sorted(list(marca_data["tipvehs"]))
                context_parts.append(f"  └─ Common tipvehs: {', '.join(tipveh_list)}")
            
            context_parts.append("")  # Empty line between marcas
        
        return "\n".join(context_parts)

    def _create_prompt(self, description: str, candidate_context: str) -> str:
        """Create structured prompt for LLM field extraction."""
        return f"""Extract vehicle information from the following description using ONLY the provided catalog options.

VEHICLE DESCRIPTION: "{description}"

AVAILABLE CATALOG OPTIONS WITH RELATIONSHIPS:
{candidate_context}

INSTRUCTIONS:
1. Extract marca (brand), submarca (sub-brand), and tipveh (vehicle type)
2. Use ONLY values from the catalog options above
3. Pay attention to the relationships: submarcas belong to specific marcas, and tipvehs are associated with certain marcas
4. Ensure your choices are consistent with the hierarchical relationships shown
5. If you're confident about a match, provide the exact value from the catalog
6. If uncertain, leave the field empty
7. Provide confidence score (0.7-0.9) for each extracted field

RESPONSE FORMAT (JSON):
{{
  "marca": {{"value": "exact_catalog_value", "confidence": 0.85}},
  "submarca": {{"value": "exact_catalog_value", "confidence": 0.80}},
  "tipveh": {{"value": "exact_catalog_value", "confidence": 0.70}}
}}

Remember: Only use combinations that exist in the catalog data above. For example, if you extract "honda" as marca, only use submarcas that are listed under HONDA.

Respond with valid JSON only."""

    def _parse_llm_response(self, llm_output: str, original_description: str) -> Optional[ExtractedFieldsWithConfidence]:
        """Parse LLM response into ExtractedFieldsWithConfidence."""
        try:
            # Extract JSON from response
            import json
            
            # Try to find JSON in the response
            json_start = llm_output.find('{')
            json_end = llm_output.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print("[ERROR] No JSON found in LLM response")
                return None
            
            json_str = llm_output[json_start:json_end]
            parsed = json.loads(json_str)
            
            # Create ExtractedFieldsWithConfidence from LLM results
            result = ExtractedFieldsWithConfidence()
            result.descveh = norm(original_description)
            
            # Process each field
            for field_name in ["marca", "submarca", "tipveh"]:
                if field_name in parsed and isinstance(parsed[field_name], dict):
                    field_data = parsed[field_name]
                    value = field_data.get("value")
                    confidence = field_data.get("confidence", 0.7)
                    
                    # Validate confidence range
                    confidence = max(0.7, min(0.9, confidence))
                    
                    field_confidence = FieldConfidence(
                        value=value if value else None,
                        confidence=confidence,
                        method="llm"
                    )
                    setattr(result, field_name, field_confidence)
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM JSON response: {e}")
            print(f"[DEBUG] LLM output: {llm_output}")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to parse LLM response: {e}")
            return None

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
        """Get extractor health status."""
        return {
            "extractor_available": True,
            "openai_available": self.openai_client is not None,
            "openai_model": self.settings.openai_model if self.openai_client else None
        }
