import re
from typing import Optional, Dict, List, Tuple
from ..models.vehicle import VehicleAttributes


class VehiclePreprocessor:
    """Preprocesses vehicle descriptions for better matching."""
    
    def __init__(self):
        # Common brand aliases and normalizations
        self.brand_aliases = {
            "GM": "GENERAL MOTORS",
            "GENERAL MOTORS": "GENERAL MOTORS",
            "TOYOTA": "TOYOTA",
            "MITSUBISHI": "MITSUBISHI",
            "NISSAN": "NISSAN",
            "HONDA": "HONDA",
            "FORD": "FORD",
            "CHEVROLET": "CHEVROLET",
            "VOLKSWAGEN": "VOLKSWAGEN",
            "VW": "VOLKSWAGEN"
        }
        
        # Common fuel type patterns
        self.fuel_patterns = {
            r'\bDIESEL\b': 'DIESEL',
            r'\bGASOLINA\b': 'GASOLINE',
            r'\bGAS\b': 'GASOLINE',
            r'\bHYBRID\b': 'HYBRID',
            r'\bELECTRIC\b': 'ELECTRIC',
            r'\bELÉCTRICO\b': 'ELECTRIC'
        }
        
        # Drivetrain patterns
        self.drivetrain_patterns = {
            r'\b4X4\b': '4X4',
            r'\b4X2\b': '4X2',
            r'\bAWD\b': 'AWD',
            r'\bFWD\b': 'FWD',
            r'\bRWD\b': 'RWD'
        }
        
        # Body style patterns
        self.body_style_patterns = {
            r'\bDC\b': 'DOUBLE_CAB',
            r'\bSC\b': 'SINGLE_CAB',
            r'\bSEDAN\b': 'SEDAN',
            r'\bSUV\b': 'SUV',
            r'\bHATCHBACK\b': 'HATCHBACK',
            r'\bPICKUP\b': 'PICKUP',
            r'\bCOUPE\b': 'COUPE',
            r'\bWAGON\b': 'WAGON'
        }
        
        # Year pattern (4 digits)
        self.year_pattern = r'\b(19|20)\d{2}\b'
        
    def clean_description(self, description: str) -> str:
        """Clean and normalize the vehicle description."""
        if not description:
            return ""
            
        # Convert to uppercase for consistency
        cleaned = description.upper().strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove special characters except spaces and alphanumeric
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        
        # Remove extra spaces again after character removal
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def remove_duplicate_brand(self, description: str) -> str:
        """Remove duplicate brand names from description."""
        words = description.split()
        if len(words) >= 2 and words[0] == words[1]:
            # Remove the first occurrence if it's a duplicate
            return ' '.join(words[1:])
        return description
    
    def extract_year(self, description: str) -> Tuple[Optional[int], str]:
        """Extract year from description and return cleaned description."""
        year_match = re.search(self.year_pattern, description)
        if year_match:
            year = int(year_match.group())
            # Remove year from description
            cleaned_desc = re.sub(self.year_pattern, '', description).strip()
            cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc)
            return year, cleaned_desc
        return None, description
    
    def extract_fuel_type(self, description: str) -> Optional[str]:
        """Extract fuel type from description."""
        for pattern, fuel_type in self.fuel_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                return fuel_type
        return None
    
    def extract_drivetrain(self, description: str) -> Optional[str]:
        """Extract drivetrain from description."""
        for pattern, drivetrain in self.drivetrain_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                return drivetrain
        return None
    
    def extract_body_style(self, description: str) -> Optional[str]:
        """Extract body style from description."""
        for pattern, body_style in self.body_style_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                return body_style
        return None
    
    def extract_brand_model(self, description: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract brand and model from description."""
        words = description.split()
        if not words:
            return None, None
            
        # First word is likely the brand
        potential_brand = words[0]
        
        # Normalize brand using aliases
        brand = self.brand_aliases.get(potential_brand, potential_brand)
        
        # Second word (or remaining words) likely form the model
        if len(words) > 1:
            model = words[1]
            return brand, model
        
        return brand, None
    
    def preprocess(self, 
                 description: str, 
                 year: Optional[int] = None,
                 known_brand: Optional[str] = None,
                 known_model: Optional[str] = None) -> Dict:
        """
        Main preprocessing function that extracts all attributes with Excel context.
        
        Args:
            description: Raw vehicle description
            year: Optional year if provided separately
            known_brand: Brand from Excel (high confidence) - takes precedence
            known_model: Model from Excel (high confidence) - takes precedence
            
        Returns:
            Dictionary with extracted attributes and cleaned description
        """
        if not description:
            return {
                "cleaned_description": "",
                "attributes": VehicleAttributes(),
                "extracted_year": None
            }
        
        # Step 1: Clean the description
        cleaned = self.clean_description(description)
        
        # Step 2: Remove duplicate brand names
        cleaned = self.remove_duplicate_brand(cleaned)
        
        # Step 3: Extract year (if not provided)
        extracted_year = year
        if not extracted_year:
            extracted_year, cleaned = self.extract_year(cleaned)
        
        # Step 4: Extract brand and model (use Excel data if available)
        if known_brand and known_model:
            # Use Excel data with high confidence
            brand, model = known_brand.upper(), known_model.upper()
        elif known_brand:
            # Use Excel brand, extract model from description
            brand = known_brand.upper()
            _, extracted_model = self.extract_brand_model(cleaned)
            model = extracted_model if extracted_model else known_model
        else:
            # Extract both from description
            brand, model = self.extract_brand_model(cleaned)
        
        # Step 5: Extract other attributes
        fuel_type = self.extract_fuel_type(cleaned)
        drivetrain = self.extract_drivetrain(cleaned)
        body_style = self.extract_body_style(cleaned)
        
        # Create attributes object (Excel data takes precedence)
        attributes = VehicleAttributes(
            brand=known_brand.upper() if known_brand else brand,
            model=known_model.upper() if known_model else model,
            year=extracted_year,
            fuel_type=fuel_type,
            drivetrain=drivetrain,
            body_style=body_style
        )
        
        return {
            "cleaned_description": cleaned,
            "attributes": attributes,
            "extracted_year": extracted_year,
            "original_description": description
        }
    
    def get_search_tokens(self, description: str) -> List[str]:
        """Get important tokens for search/matching."""
        cleaned = self.clean_description(description)
        words = cleaned.split()
        
        # Filter out common stop words and keep important terms
        stop_words = {'DE', 'DEL', 'LA', 'EL', 'CON', 'SIN', 'PARA', 'POR'}
        tokens = [word for word in words if word not in stop_words and len(word) > 1]
        
        return tokens
    
    def normalize_brand(self, brand: str) -> str:
        """Normalize brand name using aliases."""
        if not brand:
            return ""
        return self.brand_aliases.get(brand.upper(), brand.upper())
