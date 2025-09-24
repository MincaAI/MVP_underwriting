"""Vehicle input preprocessing module with unified pattern-based processing."""

import re
import json
import datetime
from typing import Optional, Dict, Tuple, Any, Union
from openai import OpenAI
from unidecode import unidecode

from ..config import get_settings


def norm(text: str) -> str:
    """Normalize text for consistent processing."""
    if not text:
        return ""
    return unidecode(str(text).strip().lower())


class VehiclePreprocessor:
    """Unified vehicle data preprocessing with pattern discovery."""

    def __init__(self):
        self.settings = get_settings()
        self.openai_client = self._initialize_openai()

    def _initialize_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client for LLM field identification assistance."""
        if self.settings.openai_api_key:
            return OpenAI(api_key=self.settings.openai_api_key)
        return None

    def _get_valid_year_range(self) -> Tuple[int, int]:
        """Calculate valid year range based on current year."""
        current_year = datetime.datetime.now().year
        min_year = self.settings.min_vehicle_year
        max_year = current_year + self.settings.future_years_ahead
        return min_year, max_year

    def process(self, input_data: Union[Dict[str, Any], Dict[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """
        Unified processing method for both single and batch inputs.

        Input formats:
        - Single: {"año": 2022, "desc": "INTERNATIONAL TRACTO"}
        - Batch: {"0": {"año": 2022, "desc": "..."}, "1": {"modelo": 2021, "descripcion": "..."}}

        Output: Always batch format {"0": {"model_year": 2022, "description": "INTERNATIONAL TRACTO"}}
        """
        # Auto-detect input format and normalize to batch
        if self._is_single_row(input_data):
            # Convert single row to batch format
            batch_data = {"0": input_data}
        else:
            batch_data = input_data

        if not batch_data:
            return {}

        # Step 1: Discover field mapping patterns from all rows
        field_patterns = self._discover_field_patterns(batch_data)

        if not field_patterns.get("year_field") or not field_patterns.get("description_field"):
            raise ValueError("Unable to identify year and description fields in input data")

        # Step 2: Apply patterns to process all rows in bulk
        result = self._apply_patterns(batch_data, field_patterns)

        return result

    def _is_single_row(self, data: Union[Dict[str, Any], Dict[str, Dict[str, Any]]]) -> bool:
        """Check if input is a single row vs batch format."""
        if not data:
            return True

        # Check if all values are dicts (batch format) or direct values (single row)
        sample_values = list(data.values())[:3]  # Check first 3 values
        dict_count = sum(1 for v in sample_values if isinstance(v, dict))

        # If more than half are dicts, it's likely batch format
        return dict_count < len(sample_values) / 2

    def _discover_field_patterns(self, batch_data: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """
        Discover field mapping patterns by analyzing all rows.

        Returns: {"year_field": "año", "description_field": "desc"}
        """
        # Collect all field names and sample their values
        field_analysis = {}

        for _, row_data in batch_data.items():
            for field_name, value in row_data.items():
                if field_name not in field_analysis:
                    field_analysis[field_name] = {
                        "values": [],
                        "year_score": 0,
                        "description_score": 0
                    }

                field_analysis[field_name]["values"].append(value)

        # Analyze each field to determine its type
        min_year, max_year = self._get_valid_year_range()

        for field_name, analysis in field_analysis.items():
            # Score as year field
            year_count = 0
            for value in analysis["values"]:
                if self._is_valid_year(value, min_year, max_year):
                    year_count += 1

            analysis["year_score"] = year_count / len(analysis["values"]) if analysis["values"] else 0

            # Score as description field
            desc_scores = []
            for value in analysis["values"]:
                if isinstance(value, str) and len(str(value).strip()) > 3:
                    desc_scores.append(self._calculate_description_score(str(value)))
                else:
                    desc_scores.append(0)

            analysis["description_score"] = sum(desc_scores) / len(desc_scores) if desc_scores else 0

        # Find best matches for each type
        year_candidates = [(f, analysis["year_score"]) for f, analysis in field_analysis.items()
                          if analysis["year_score"] > 0.3]
        desc_candidates = [(f, analysis["description_score"]) for f, analysis in field_analysis.items()
                          if analysis["description_score"] > 0.2]

        # Sort by score
        year_candidates.sort(key=lambda x: x[1], reverse=True)
        desc_candidates.sort(key=lambda x: x[1], reverse=True)

        year_field = year_candidates[0][0] if year_candidates else None
        description_field = desc_candidates[0][0] if desc_candidates else None

        # If no good matches found, use LLM
        if not year_field or not description_field:
            llm_result = self._llm_identify_fields(batch_data, field_analysis)
            if llm_result:
                if not year_field and llm_result.get("year_field"):
                    year_field = llm_result["year_field"]
                if not description_field and llm_result.get("description_field"):
                    description_field = llm_result["description_field"]

        return {
            "year_field": year_field,
            "description_field": description_field,
            "year_candidates": [f for f, _ in year_candidates],
            "desc_candidates": [f for f, _ in desc_candidates]
        }

    def _is_valid_year(self, value: Any, min_year: int, max_year: int) -> bool:
        """Check if a value is a valid year."""
        try:
            if isinstance(value, int):
                return min_year <= value <= max_year

            if isinstance(value, str) and value.strip():
                # Try direct conversion
                year_int = int(value.strip())
                return min_year <= year_int <= max_year

        except (ValueError, TypeError):
            pass

        return False

    def _calculate_description_score(self, text: str) -> float:
        """Calculate likelihood that text is a vehicle description."""
        if not text or not isinstance(text, str):
            return 0.0

        score = 0.0
        text_lower = text.lower()

        # Length bonus
        if len(text) > 10:
            score += 0.3
        if len(text) > 20:
            score += 0.2

        # Vehicle-related keywords
        vehicle_keywords = [
            'toyota', 'honda', 'nissan', 'ford', 'chevrolet', 'volkswagen', 'bmw', 'mercedes',
            'audi', 'hyundai', 'kia', 'mazda', 'subaru', 'renault', 'peugeot', 'citroen',
            'international', 'volvo', 'scania', 'man', 'freightliner', 'peterbilt',
            'sedan', 'suv', 'hatchback', 'pickup', 'coupe', 'convertible', 'tracto', 'truck',
            'auto', 'car', 'vehicle', 'carro', 'automovil', 'vehiculo',
            'motor', 'engine', 'cilindros', 'turbo', 'hybrid', 'electric'
        ]

        keyword_matches = sum(1 for keyword in vehicle_keywords if keyword in text_lower)
        score += keyword_matches * 0.2

        # Penalize if it looks like an ID or code
        if re.match(r'^[A-Z0-9_-]+$', text.strip()):
            score -= 0.5

        # Penalize if it's just numbers
        if text.strip().isdigit():
            score -= 0.8

        return max(0.0, score)

    def _apply_patterns(self, batch_data: Dict[str, Dict[str, Any]], patterns: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """Apply discovered patterns to process all rows efficiently."""
        result = {}
        primary_year_field = patterns["year_field"]
        primary_desc_field = patterns["description_field"]
        year_candidates = patterns.get("year_candidates", [primary_year_field] if primary_year_field else [])
        desc_candidates = patterns.get("desc_candidates", [primary_desc_field] if primary_desc_field else [])
        min_year, max_year = self._get_valid_year_range()

        for row_id, row_data in batch_data.items():
            try:
                # Extract year - try multiple candidates
                year = None
                for year_field in year_candidates:
                    if year_field in row_data:
                        year_value = row_data[year_field]
                        year = self._extract_year(year_value, min_year, max_year)
                        if year:
                            break

                # Extract description - try multiple candidates
                description = None
                for desc_field in desc_candidates:
                    if desc_field in row_data:
                        description_value = row_data[desc_field]
                        description = self._normalize_text(str(description_value))
                        if description and len(description.strip()) > 2:
                            break

                if year and description:
                    result[row_id] = {
                        "model_year": year,
                        "description": description
                    }

            except Exception:
                # Skip rows that can't be processed
                continue

        return result

    def _extract_year(self, value: Any, min_year: int, max_year: int) -> Optional[int]:
        """Extract year from a field value."""
        if isinstance(value, int):
            return value if min_year <= value <= max_year else None

        if isinstance(value, str) and value.strip():
            try:
                year_int = int(value.strip())
                return year_int if min_year <= year_int <= max_year else None
            except ValueError:
                # Try to extract from text
                year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', value)
                for year_str in year_matches:
                    year_int = int(year_str)
                    if min_year <= year_int <= max_year:
                        return year_int

        return None

    def _normalize_text(self, text: str) -> str:
        """Clean and normalize text data."""
        if not text:
            return ""

        # Basic cleaning
        cleaned = str(text).strip()

        # Remove VIN patterns (17-character alphanumeric, excludes I, O, Q)
        vin_pattern = r'\b[A-HJ-NPR-Z0-9]{17}\b'
        cleaned = re.sub(vin_pattern, '', cleaned)

        # Remove extra whitespace and strip leading/trailing spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Remove consecutive duplicate words (e.g., "tanque tanque" → "tanque")
        cleaned = self._remove_duplicate_words(cleaned)

        # Apply full normalization like original norm() function
        return unidecode(cleaned.lower())

    def _remove_duplicate_words(self, text: str) -> str:
        """Remove consecutive duplicate words like 'tanque tanque' → 'tanque'."""
        if not text:
            return ""
        
        words = text.lower().split()
        result = []
        prev_word = None
        
        for word in words:
            if word != prev_word:
                result.append(word)
            prev_word = word
        
        return ' '.join(result)

    def _llm_identify_fields(self, batch_data: Dict[str, Dict[str, Any]], field_analysis: Dict) -> Optional[Dict[str, str]]:
        """Use LLM to identify fields when pattern analysis is uncertain."""
        if not self.openai_client:
            return None

        min_year, max_year = self._get_valid_year_range()

        # Prepare sample data for LLM (limit size)
        sample_data = {}
        for i, (_, row_data) in enumerate(list(batch_data.items())[:3]):
            sample_data[f"row_{i}"] = {k: str(v)[:50] for k, v in row_data.items()}

        # Include field analysis scores
        field_scores = {}
        for field_name, analysis in field_analysis.items():
            field_scores[field_name] = {
                "year_score": round(analysis["year_score"], 2),
                "description_score": round(analysis["description_score"], 2)
            }

        prompt = f'''Analyze this vehicle data and identify the field names for year and description:

Sample Data:
{json.dumps(sample_data, indent=2)}

Field Analysis Scores:
{json.dumps(field_scores, indent=2)}

Requirements:
- Year field: Contains years between {min_year} and {max_year}
- Description field: Contains vehicle descriptions (brand, model, type)

Return ONLY valid JSON in this exact format:
{{"year_field": "field_name_here", "description_field": "field_name_here"}}

If uncertain about any field, set it to null.'''

        try:
            response = self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)

        except Exception:
            pass

        return None

    def get_health_status(self) -> Dict[str, Any]:
        """Get preprocessor health status."""
        return {
            "openai_available": self.openai_client is not None,
            "openai_model": self.settings.openai_model,
            "year_range": self._get_valid_year_range(),
            "processing_mode": "unified_pattern_based"
        }
