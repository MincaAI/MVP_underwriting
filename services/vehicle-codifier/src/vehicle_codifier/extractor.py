"""Vehicle field extraction module for CATVER fields."""

import re
import json
from typing import Optional, Set, Dict, Tuple
from openai import OpenAI
from rapidfuzz import fuzz
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from .models import ExtractedFields, ExtractedFieldsWithConfidence, FieldConfidence
from .config import get_settings
from .utils import norm


class VehicleExtractor:
    """Catalog-driven field extraction with confidence scoring and LLM fallback."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)
        self.openai_client = self._initialize_openai()

    def _initialize_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client for LLM fallback."""
        if self.settings.openai_api_key:
            return OpenAI(api_key=self.settings.openai_api_key)
        return None

    def extract_fields_with_year(self, description: str, year: int) -> ExtractedFields:
        """Extract fields using catalog-driven approach."""
        result_with_confidence = self.extract_fields_with_confidence(description, year)
        return result_with_confidence.to_extracted_fields()

    def extract_fields_with_confidence_and_year(self, description: str, year: int) -> ExtractedFieldsWithConfidence:
        """Extract fields with confidence scores using catalog-driven approach."""
        return self.extract_fields_with_confidence(description, year)

    def extract_fields_with_confidence(self, description: str, year: int) -> ExtractedFieldsWithConfidence:
        """Extract fields using catalog-driven approach with confidence scoring and iterative text removal."""

        # Step 1: Build year-filtered candidates
        candidates = self._build_year_filtered_candidates(year)

        if not candidates:
            # No candidates for this year, return completely empty result
            return ExtractedFieldsWithConfidence()

        # Step 2: Initialize result and working description
        result = ExtractedFieldsWithConfidence()
        print('===description>', description);
        result.descveh = norm(description)
        working_description = description

        # Step 3: Extract marca first (highest priority)
        result.marca = self._extract_field_with_confidence(
            working_description, candidates["marca"], "marca"
        )

        # Remove marca from working description if confidence >= 0.9
        if result.marca.value and result.marca.confidence >= 0.9:
            working_description = self._remove_matched_text(working_description, result.marca.value)
            print(f"🔧 Removed '{result.marca.value}' from description (confidence: {result.marca.confidence:.3f})")
            print(f"   Working description now: '{working_description}'")

        # Step 4: Filter submarca candidates by extracted marca if available
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
            print(f"🔧 Removed '{result.submarca.value}' from description (confidence: {result.submarca.confidence:.3f})")
            print(f"   Working description now: '{working_description}'")

        # Step 5: Extract cvesegm from cleaned description
        result.cvesegm = self._extract_field_with_confidence(
            working_description, candidates["cvesegm"], "cvesegm"
        )

        # Remove cvesegm from working description if confidence >= 0.9
        if result.cvesegm.value and result.cvesegm.confidence >= 0.9:
            working_description = self._remove_matched_text(working_description, result.cvesegm.value)
            print(f"🔧 Removed '{result.cvesegm.value}' from description (confidence: {result.cvesegm.confidence:.3f})")
            print(f"   Working description now: '{working_description}'")

        # Step 6: Extract tipveh from cleaned description
        result.tipveh = self._extract_field_with_confidence(
            working_description, candidates["tipveh"], "tipveh"
        )

        # Note: No need to remove tipveh since it's the last field

        # Step 7: Apply LLM fallback for low-confidence fields using original description
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
                        candidates["marca"].add(row.marca.strip().upper())
                    if row.submarca and row.submarca.strip():
                        candidates["submarca"].add(row.submarca.strip().upper())
                    if row.cvesegm and row.cvesegm.strip():
                        candidates["cvesegm"].add(row.cvesegm.strip().upper())
                    if row.tipveh and row.tipveh.strip():
                        candidates["tipveh"].add(row.tipveh.strip().upper())

                print(f"📋 Year {year} candidates: marca={len(candidates['marca'])}, submarca={len(candidates['submarca'])}, cvesegm={len(candidates['cvesegm'])}, tipveh={len(candidates['tipveh'])}")
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
                    row.submarca.strip().upper()
                    for row in result.fetchall()
                    if row.submarca and row.submarca.strip()
                }

                print(f"🔍 Filtered submarca candidates by '{marca}': {len(filtered_submarcas)} options")
                return filtered_submarcas

        except Exception as e:
            print(f"⚠️ Failed to filter submarca by marca '{marca}': {e}")
            return candidates["submarca"]

    def _get_candidates_with_frequencies(self, year: int, fields: list) -> Dict[str, Dict[str, int]]:
        """Get candidates with their frequency counts for better LLM prompts."""
        try:
            with Session(self.engine) as session:
                candidates_with_freq = {}

                for field in fields:
                    if field in ["marca", "submarca", "cvesegm", "tipveh"]:
                        result = session.execute(text(f"""
                            SELECT {field}, COUNT(*) as frequency
                            FROM amis_catalog
                            WHERE modelo = :year
                              AND {field} IS NOT NULL
                              AND catalog_version = (
                                  SELECT version FROM catalog_import
                                  WHERE status IN ('ACTIVE', 'LOADED')
                                  ORDER BY version DESC LIMIT 1
                              )
                            GROUP BY {field}
                            ORDER BY frequency DESC, {field}
                        """), {"year": year})

                        field_candidates = {}
                        for row in result.fetchall():
                            if row[0] and row[0].strip():
                                field_candidates[row[0].strip().upper()] = row.frequency

                        candidates_with_freq[field] = field_candidates

                return candidates_with_freq

        except Exception as e:
            print(f"⚠️ Failed to get candidates with frequencies: {e}")
            return {}

    def _get_smart_submarca_candidates(self, year: int, marca: str = None) -> Dict[str, int]:
        """Get submarca candidates with frequencies, optionally filtered by marca."""
        try:
            with Session(self.engine) as session:
                if marca:
                    # Get submarcas for specific marca
                    result = session.execute(text("""
                        SELECT submarca, COUNT(*) as frequency
                        FROM amis_catalog
                        WHERE modelo = :year
                          AND marca ILIKE :marca
                          AND submarca IS NOT NULL
                          AND catalog_version = (
                              SELECT version FROM catalog_import
                              WHERE status IN ('ACTIVE', 'LOADED')
                              ORDER BY version DESC LIMIT 1
                          )
                        GROUP BY submarca
                        ORDER BY frequency DESC, submarca
                    """), {"year": year, "marca": marca})
                else:
                    # Get all submarcas for the year
                    result = session.execute(text("""
                        SELECT submarca, COUNT(*) as frequency
                        FROM amis_catalog
                        WHERE modelo = :year
                          AND submarca IS NOT NULL
                          AND catalog_version = (
                              SELECT version FROM catalog_import
                              WHERE status IN ('ACTIVE', 'LOADED')
                              ORDER BY version DESC LIMIT 1
                          )
                        GROUP BY submarca
                        ORDER BY frequency DESC, submarca
                    """), {"year": year})

                submarca_candidates = {}
                for row in result.fetchall():
                    if row.submarca and row.submarca.strip():
                        submarca_candidates[row.submarca.strip().upper()] = row.frequency

                return submarca_candidates

        except Exception as e:
            print(f"⚠️ Failed to get smart submarca candidates: {e}")
            return {}

    def _extract_field_with_confidence(
        self, description: str, candidates: Set[str], field_type: str = "unknown"
    ) -> FieldConfidence:
        """Extract single field using multi-stage matching with confidence scoring."""

        if not candidates:
            return FieldConfidence(value=None, confidence=0.0, method="none")

        desc_upper = description.upper()

        # Stage 1: Direct substring matching (highest confidence)
        for candidate in candidates:
            if candidate in desc_upper:
                return FieldConfidence(
                    value=candidate,
                    confidence=1.0,
                    method="direct"
                )

        # Stage 2: Fuzzy matching (medium to high confidence)
        best_match = None
        best_score = 0.0
        best_method = "fuzzy"

        for candidate in candidates:
            # Try partial ratio for substring matching
            partial_score = fuzz.partial_ratio(desc_upper, candidate) / 100.0
            if partial_score > best_score:
                best_match = candidate
                best_score = partial_score
                best_method = "fuzzy_partial"

            # Try token sort ratio for word order flexibility
            token_score = fuzz.token_sort_ratio(desc_upper, candidate) / 100.0
            if token_score > best_score:
                best_match = candidate
                best_score = token_score
                best_method = "fuzzy_token"

        # Apply confidence thresholds
        if best_score >= 0.8:
            confidence = min(0.95, best_score)  # Cap at 0.95 for fuzzy matches
            return FieldConfidence(
                value=best_match,
                confidence=confidence,
                method=best_method
            )
        
        else:
            # Stage 3: LLM matching for low confidence cases (< 0.8)
            if self.openai_client and candidates:
                llm_result = self._llm_single_field_extraction(description, candidates, field_type)
                if llm_result.confidence > 0.0:  # Use LLM result if it found something
                    print(f"🤖 LLM fallback for {field_type}: {llm_result.value} (confidence: {llm_result.confidence:.3f})")
                    return llm_result

            # Return fuzzy result or none if no LLM improvement
            if best_score >= 0.6:
                confidence = best_score * 0.8
            elif best_score >= 0.4:
                confidence = best_score * 0.6  # Further reduce for weak matches
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

        # Generate LLM prompt for missing fields only
        llm_result = self._llm_extract_specific_fields(description, low_confidence_fields, candidates)

        # Update result with LLM extractions
        for field_name in low_confidence_fields:
            if hasattr(llm_result, field_name):
                llm_field = getattr(llm_result, field_name)
                if llm_field.confidence > getattr(result, field_name).confidence:
                    setattr(result, field_name, llm_field)

        return result

    def _llm_extract_specific_fields(
        self, description: str, fields: list, candidates: Dict[str, Set[str]]
    ) -> ExtractedFieldsWithConfidence:
        """Use LLM to extract specific fields with enhanced candidate validation."""

        # Get the year from description or use default
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', description)
        year = int(year_match.group(1)) if year_match else 2022

        # Get candidates with frequencies for better prompting
        candidates_with_freq = self._get_candidates_with_frequencies(year, fields)

        # Build enhanced candidates table for prompt
        candidates_sections = []

        for field in fields:
            if field in candidates_with_freq and candidates_with_freq[field]:
                field_candidates = candidates_with_freq[field]

                # Sort by frequency (most common first) and limit to reasonable number
                sorted_candidates = sorted(field_candidates.items(), key=lambda x: x[1], reverse=True)

                if field == "submarca":
                    # For submarca, limit to top 20 to avoid overwhelming the LLM
                    sorted_candidates = sorted_candidates[:20]
                elif field in ["marca", "cvesegm", "tipveh"]:
                    # For other fields, show more options as they're usually fewer
                    sorted_candidates = sorted_candidates[:30]

                # Format candidates with frequency indicators
                formatted_candidates = []
                for candidate, freq in sorted_candidates:
                    if freq >= 10:
                        formatted_candidates.append(f"{candidate} (common)")
                    elif freq >= 3:
                        formatted_candidates.append(f"{candidate} (moderate)")
                    else:
                        formatted_candidates.append(f"{candidate} (rare)")

                candidates_sections.append(f"- {field.upper()}: {', '.join(formatted_candidates)}")

        candidates_text = "\n".join(candidates_sections)

        # Enhanced prompt with better instructions
        prompt = f'''Extract vehicle information from this description for year {year}:

DESCRIPTION: "{description}"

AVAILABLE CATALOG OPTIONS:
{candidates_text}

EXTRACTION RULES:
1. Extract ONLY these fields: {', '.join(fields)}
2. Use ONLY values from the catalog options above
3. Ignore VIN numbers, serial numbers, and license plates
4. If a field cannot be determined from the description, use null
5. Common values are more likely to be correct

SPECIAL NOTES:
- VIN numbers are 17-character alphanumeric codes (like "3HSDZAPT7NN354987") - IGNORE these
- TRACTO vehicles usually have tipveh="TRACTO CAMION" in the catalog
- Prefer exact substring matches from the description

Return ONLY valid JSON with these exact field names:
{{"marca": "VALUE_OR_NULL", "submarca": "VALUE_OR_NULL", "cvesegm": "VALUE_OR_NULL", "tipveh": "VALUE_OR_NULL"}}'''

        try:
            response = self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.05,  # Lower temperature for more consistent results
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)

                # Enhanced validation and create result
                result = ExtractedFieldsWithConfidence()

                for field in fields:
                    if field in data and data[field] and data[field].upper() != "NULL":
                        value = data[field].upper()
                        confidence = 0.3  # Default low confidence
                        method = "llm"

                        # Enhanced validation against candidates
                        if field in candidates and value in candidates[field]:
                            # Check frequency for confidence adjustment
                            if field in candidates_with_freq and value in candidates_with_freq[field]:
                                freq = candidates_with_freq[field][value]
                                if freq >= 10:
                                    confidence = 0.9  # Very high for common values
                                elif freq >= 3:
                                    confidence = 0.8  # High for moderate values
                                else:
                                    confidence = 0.7  # Good for rare but valid values
                                method = "llm_validated"
                            else:
                                confidence = 0.8  # Good for valid but unknown frequency
                                method = "llm_validated"
                        else:
                            # Value not in candidates - try fuzzy matching
                            if field in candidates:
                                best_match, best_score = self._find_best_candidate_match(value, candidates[field])
                                if best_match and best_score >= 0.9:
                                    print(f"🔧 LLM result '{value}' fuzzy-matched to '{best_match}' (score: {best_score:.2f})")
                                    value = best_match
                                    confidence = 0.7
                                    method = "llm_corrected"
                                else:
                                    print(f"⚠️ LLM result '{value}' not found in {field} candidates")
                                    confidence = 0.3
                                    method = "llm_unvalidated"

                        setattr(result, field, FieldConfidence(
                            value=value,
                            confidence=confidence,
                            method=method
                        ))

                return result

        except Exception as e:
            print(f"⚠️ Enhanced LLM extraction failed: {e}")

        return ExtractedFieldsWithConfidence()

    def _find_best_candidate_match(self, value: str, candidates: Set[str]) -> Tuple[Optional[str], float]:
        """Find the best fuzzy match for a value in candidates."""
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = fuzz.ratio(value.upper(), candidate.upper()) / 100.0
            if score > best_score:
                best_match = candidate
                best_score = score

        return best_match, best_score

    def _llm_single_field_extraction(self, description: str, candidates: Set[str], field_type: str) -> FieldConfidence:
        """Use LLM to extract a single field from candidates."""
        if not self.openai_client or not candidates:
            return FieldConfidence(value=None, confidence=0.0, method="none")

        # Create candidates list sorted by frequency if possible
        candidates_list = sorted(list(candidates))
        candidates_text = ", ".join(candidates_list)  # Limit to top 20

        prompt = f'''Extract the {field_type} from this vehicle description using ONLY the provided candidates.

Description: "{description}"

Valid {field_type} candidates: {candidates_text}

Rules:
- Return ONLY a value from the candidates list above, or null if no match
- Ignore VIN numbers, license plates, serial numbers
- Use exact spelling from candidates list
- If {field_type} is not mentioned in the description, return null with confidence 0

Return JSON format:
{{"value": "EXACT_CANDIDATE_OR_null", "confidence": 0-100, "explanation": "reasoning for decision"}}

Examples:
- Good match: {{"value": "TOYOTA", "confidence": 95, "explanation": "TOYOTA clearly mentioned in description"}}
- No {field_type}: {{"value": null, "confidence": 0, "explanation": "No {field_type} information in description"}}
- Uncertain: {{"value": "FORD", "confidence": 60, "explanation": "Partial match but unclear"}}'''

        try:
            response = self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.05,
                max_tokens=150  # Increased for JSON response
            )

            content = response.choices[0].message.content.strip()

            # Try to parse JSON response
            try:
                llm_response = json.loads(content)
                llm_value = llm_response.get("value")
                llm_confidence = llm_response.get("confidence", 0)
                llm_explanation = llm_response.get("explanation", "")

                # Convert confidence from 0-100 to 0.0-1.0
                confidence_score = min(max(float(llm_confidence) / 100.0, 0.0), 1.0)

                print(f"🤖 LLM {field_type} response: {llm_value} (confidence: {llm_confidence}%, explanation: {llm_explanation})")

                # Handle null/none values
                if llm_value is None or str(llm_value).upper() in ['NULL', 'NONE', '']:
                    return FieldConfidence(value=None, confidence=confidence_score, method="llm")

                # Clean and validate the value
                clean_value = str(llm_value).strip().upper()

                # Validate against candidates
                if clean_value in candidates:
                    # Use LLM confidence for exact match
                    return FieldConfidence(value=clean_value, confidence=confidence_score, method="llm_validated")
                else:
                    # Try fuzzy matching against candidates
                    best_match, best_score = self._find_best_candidate_match(clean_value, candidates)
                    if best_match and best_score >= 90:
                        # Lower confidence for corrected matches
                        corrected_confidence = min(confidence_score * 0.8, 0.75)
                        print(f"🔧 LLM value '{clean_value}' corrected to '{best_match}' (fuzzy score: {best_score})")
                        return FieldConfidence(value=best_match, confidence=corrected_confidence, method="llm_corrected")

                return FieldConfidence(value=None, confidence=0.0, method="llm")

            except json.JSONDecodeError:
                # Fallback to old parsing if JSON fails
                print(f"⚠️ Failed to parse JSON response, falling back to simple parsing: {content}")
                clean_content = content.replace('"', '').replace("'", '').strip().upper()

                if clean_content in ['NULL', 'NONE', '']:
                    return FieldConfidence(value=None, confidence=0.0, method="llm")

                # Validate against candidates
                if clean_content in candidates:
                    return FieldConfidence(value=clean_content, confidence=0.7, method="llm_fallback")
                else:
                    # Try fuzzy matching
                    best_match, best_score = self._find_best_candidate_match(clean_content, candidates)
                    if best_match and best_score >= 90:
                        return FieldConfidence(value=best_match, confidence=0.6, method="llm_fallback_corrected")

                return FieldConfidence(value=None, confidence=0.0, method="llm")

        except Exception as e:
            print(f"⚠️ LLM single field extraction failed for {field_type}: {e}")
            return FieldConfidence(value=None, confidence=0.0, method="llm_error")

    def _remove_matched_text(self, description: str, matched_value: str) -> str:
        """Remove matched text from description to clean it for subsequent extractions."""
        if not matched_value or not description:
            return description

        desc_upper = description.upper()
        matched_upper = matched_value.upper()

        # Try exact substring removal first
        if matched_upper in desc_upper:
            # Find the position and remove it
            start_pos = desc_upper.find(matched_upper)
            end_pos = start_pos + len(matched_upper)
            cleaned = description[:start_pos] + description[end_pos:]
            # Clean up extra whitespace
            cleaned = ' '.join(cleaned.split())
            return cleaned.strip()

        # Try fuzzy matching to find the best position to remove
        words = description.split()
        best_match_indices = []
        best_score = 0.0

        # Try different word combinations
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):  # Try up to 3-word combinations
                word_combo = ' '.join(words[i:j])
                score = fuzz.ratio(word_combo.upper(), matched_upper) / 100.0
                if score > best_score and score >= 0.8:  # High similarity threshold
                    best_score = score
                    best_match_indices = list(range(i, j))

        # Remove the best matching words
        if best_match_indices:
            filtered_words = [word for idx, word in enumerate(words) if idx not in best_match_indices]
            cleaned = ' '.join(filtered_words)
            return cleaned.strip()

        # If no good match found, return original description
        return description

    def _llm_fallback_all_fields(self, description: str) -> ExtractedFieldsWithConfidence:
        """Full LLM fallback when no catalog candidates available."""
        if not self.openai_client:
            return ExtractedFieldsWithConfidence(descveh=norm(description))

        # Use existing _llm_extraction logic but return with confidence scores
        try:
            # Simplified LLM prompt for all fields
            prompt = f'''Extract vehicle information from: "{description}"

Return JSON with: marca, submarca, cvesegm, tipveh (use null if unknown)'''

            response = self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )

            content = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)

            if json_match:
                data = json.loads(json_match.group(0))
                result = ExtractedFieldsWithConfidence(descveh=norm(description))

                for field in ["marca", "submarca", "cvesegm", "tipveh"]:
                    if field in data and data[field]:
                        setattr(result, field, FieldConfidence(
                            value=data[field].upper(),
                            confidence=0.7,  # Medium confidence for unconstrained LLM
                            method="llm_fallback"
                        ))

                return result

        except Exception as e:
            print(f"❌ LLM fallback failed: {e}")

        return ExtractedFieldsWithConfidence(descveh=norm(description))

    def get_health_status(self) -> dict:
        """Get extractor health status."""
        return {
            "catalog_driven": True,
            "database_available": True,  # Could add actual DB health check
            "openai_available": self.openai_client is not None,
            "openai_model": self.settings.openai_model
        }