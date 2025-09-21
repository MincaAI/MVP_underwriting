"""Brand lookup module for enhanced vehicle brand detection."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz


class BrandLookup:
    """Enhanced brand detection using AMIS catalog data."""

    def __init__(self):
        self.brand_aliases: Dict[str, str] = {}
        self.brand_data: Dict[str, dict] = {}
        self.commercial_brands: Set[str] = set()
        self._load_brand_data()

    def _load_brand_data(self):
        """Load brand lookup data from JSON files."""
        try:
            # Load brand aliases
            aliases_path = Path(__file__).parent.parent.parent / "brand_aliases.json"
            if aliases_path.exists():
                with open(aliases_path, 'r', encoding='utf-8') as f:
                    self.brand_aliases = json.load(f)

            # Load brand metadata
            brand_data_path = Path(__file__).parent.parent.parent / "brand_lookup_data.json"
            if brand_data_path.exists():
                with open(brand_data_path, 'r', encoding='utf-8') as f:
                    brand_list = json.load(f)

                    # Convert to dict and identify commercial brands
                    for brand in brand_list:
                        brand_name = brand["brand_name"]
                        self.brand_data[brand_name] = brand

                        # Identify commercial vehicle brands (store in uppercase)
                        vehicle_types = brand.get("vehicle_types", [])
                        if any(vtype in ["CAMION", "TRACTO CAMION", "SEMIREMOLQUE"]
                               for vtype in vehicle_types):
                            self.commercial_brands.add(brand_name.upper())

            print(f"📋 Loaded {len(self.brand_aliases)} brand aliases")
            print(f"🚛 Identified {len(self.commercial_brands)} commercial brands")

        except Exception as e:
            print(f"⚠️ Warning: Could not load brand data: {e}")
            # Initialize with basic fallback
            self._initialize_fallback()

    def _initialize_fallback(self):
        """Initialize with basic brand data as fallback."""
        basic_brands = {
            'FREIGHTLINER': 'FREIGHTLINER',
            'INTERNATIONAL': 'INTERNATIONAL',
            'KENWORTH': 'KENWORTH',
            'PETERBILT': 'PETERBILT',
            'MACK': 'MACK',
            'VOLVO': 'VOLVO',
            'BMW': 'BMW',
            'TOYOTA': 'TOYOTA',
            'FORD': 'FORD',
            'CHEVROLET': 'CHEVROLET'
        }
        self.brand_aliases.update(basic_brands)
        self.commercial_brands.update(['FREIGHTLINER', 'INTERNATIONAL', 'KENWORTH', 'PETERBILT'])

    def extract_brand(self, description: str) -> Optional[str]:
        """Extract brand from vehicle description using enhanced lookup."""
        brand, _ = self.extract_brand_with_confidence(description)
        return brand

    def extract_brand_with_confidence(self, description: str) -> Tuple[Optional[str], float]:
        """Extract brand with confidence score from vehicle description.

        Returns:
            Tuple[brand_name, confidence_score] where confidence is 0.0-1.0
        """
        desc_clean = self._clean_description(description)

        # Method 1: Exact alias matching (highest confidence)
        brand = self._exact_alias_match(desc_clean)
        if brand:
            return brand, 1.0

        # Method 2: Fuzzy matching for partial matches
        brand, fuzzy_score = self._fuzzy_brand_match_with_score(desc_clean)
        if brand:
            # Convert fuzzy score to confidence: 80+ = high, 90+ = very high
            if fuzzy_score >= 90.0:
                confidence = 0.90 + (fuzzy_score - 90.0) / 100.0  # 0.90-0.95
            else:
                confidence = 0.70 + (fuzzy_score - 80.0) / 50.0   # 0.70-0.89
            return brand, confidence

        # Method 3: Regex pattern matching (good confidence)
        brand = self._regex_brand_match(desc_clean)
        if brand:
            return brand, 0.85

        return None, 0.0

    def _clean_description(self, description: str) -> str:
        """Clean and normalize description for brand extraction."""
        # Remove extra whitespace and special characters
        desc = re.sub(r'\s+', ' ', description.strip().upper())
        desc = re.sub(r'[^\w\s]', ' ', desc)
        return desc

    def _exact_alias_match(self, description: str) -> Optional[str]:
        """Find exact matches using brand aliases."""
        words = description.split()

        # Check individual words
        for word in words:
            if word in self.brand_aliases:
                return self.brand_aliases[word]

        # Check word combinations
        for i in range(len(words) - 1):
            combo = f"{words[i]} {words[i+1]}"
            if combo in self.brand_aliases:
                return self.brand_aliases[combo]

        return None

    def _fuzzy_brand_match(self, description: str, threshold: float = 80.0) -> Optional[str]:
        """Find brands using fuzzy string matching."""
        brand, _ = self._fuzzy_brand_match_with_score(description, threshold)
        return brand

    def _fuzzy_brand_match_with_score(self, description: str, threshold: float = 80.0) -> Tuple[Optional[str], float]:
        """Find brands using fuzzy string matching with confidence score."""
        best_match = None
        best_score = 0.0

        for alias, brand in self.brand_aliases.items():
            # Skip very short aliases to avoid false matches
            if len(alias) < 3:
                continue

            score = fuzz.partial_ratio(alias, description)
            if score > threshold and score > best_score:
                best_score = score
                best_match = brand

        return best_match, best_score

    def _regex_brand_match(self, description: str) -> Optional[str]:
        """Find brands using regex patterns."""
        # Common commercial truck patterns
        commercial_patterns = [
            r'\b(freightliner|international|kenworth|peterbilt|mack|volvo)\b',
            r'\b(fr?eight?liner|int[er]*national)\b',
            r'\btr\s+(freightliner|international)\b'
        ]

        for pattern in commercial_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                brand_text = match.group(1).upper()
                if brand_text in self.brand_aliases:
                    return self.brand_aliases[brand_text]

        return None

    def is_commercial_brand(self, brand: str) -> bool:
        """Check if brand is primarily commercial vehicles."""
        return brand in self.commercial_brands

    def get_brand_info(self, brand: str) -> Optional[dict]:
        """Get metadata for a brand."""
        return self.brand_data.get(brand)

    def get_vehicle_types_for_brand(self, brand: str) -> List[str]:
        """Get vehicle types associated with a brand."""
        brand_info = self.get_brand_info(brand)
        if brand_info:
            return brand_info.get("vehicle_types", [])
        return []

    def suggest_tipveh(self, brand: str, description: str) -> str:
        """Suggest vehicle type based on brand and description."""
        desc_upper = description.upper()

        # Commercial vehicle indicators
        if (self.is_commercial_brand(brand) or
            any(word in desc_upper for word in ['TRACTO', 'CAMION', 'TRUCK', 'SEMI'])):
            return 'camioneta'

        # Motorcycle indicators
        if any(word in desc_upper for word in ['MOTOCICLETA', 'MOTO', 'MOTORCYCLE']):
            return 'motocicleta'

        # Default to auto
        return 'auto'

    def get_health_status(self) -> dict:
        """Get brand lookup health status."""
        return {
            "brand_lookup_loaded": len(self.brand_aliases) > 0,
            "total_aliases": len(self.brand_aliases),
            "commercial_brands": len(self.commercial_brands),
            "brand_data_available": len(self.brand_data) > 0
        }