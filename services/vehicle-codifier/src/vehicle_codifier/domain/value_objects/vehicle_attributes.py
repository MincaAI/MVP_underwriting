"""Vehicle attributes value object."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VehicleAttributes:
    """Immutable value object representing vehicle attributes."""
    
    # Core attributes (from Excel - high confidence)
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vin: Optional[str] = None
    coverage_package: Optional[str] = None
    
    # Enhanced attributes (from LLM extraction - medium confidence)
    fuel_type: Optional[str] = None  # DIESEL, GASOLINA, etc.
    drivetrain: Optional[str] = None  # 4X4, 4X2, etc.
    body_style: Optional[str] = None  # DOUBLE_CAB, SEDAN, etc.
    trim_level: Optional[str] = None  # DENALI, PREMIUM, etc.
    
    # Additional attributes
    engine_size: Optional[str] = None
    transmission: Optional[str] = None  # MANUAL, AUTOMATICO
    doors: Optional[int] = None
    
    # Confidence tracking
    excel_confidence: float = 0.0  # 0.0 to 1.0
    llm_confidence: float = 0.0    # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate value object invariants."""
        if self.year is not None and (self.year < 1900 or self.year > 2030):
            raise ValueError(f"Invalid year: {self.year}")
        
        if self.doors is not None and (self.doors < 2 or self.doors > 6):
            raise ValueError(f"Invalid doors: {self.doors}")
        
        if not (0.0 <= self.excel_confidence <= 1.0):
            raise ValueError(f"Excel confidence must be between 0.0 and 1.0: {self.excel_confidence}")
        
        if not (0.0 <= self.llm_confidence <= 1.0):
            raise ValueError(f"LLM confidence must be between 0.0 and 1.0: {self.llm_confidence}")
    
    @property
    def has_core_attributes(self) -> bool:
        """Check if core attributes (brand, model, year) are present."""
        return all([self.brand, self.model, self.year])
    
    @property
    def has_excel_data(self) -> bool:
        """Check if any Excel data is present."""
        return any([
            self.brand, self.model, self.year, 
            self.vin, self.coverage_package
        ]) and self.excel_confidence > 0.0
    
    @property
    def has_enhanced_attributes(self) -> bool:
        """Check if enhanced attributes are present."""
        return any([
            self.fuel_type, self.drivetrain, self.body_style,
            self.trim_level, self.engine_size, self.transmission
        ])
    
    @property
    def completeness_score(self) -> float:
        """Calculate overall attribute completeness (0.0 to 1.0)."""
        all_attributes = [
            self.brand, self.model, self.year, self.vin,
            self.fuel_type, self.drivetrain, self.body_style,
            self.trim_level, self.engine_size, self.transmission
        ]
        
        filled_count = sum(1 for attr in all_attributes if attr is not None)
        return filled_count / len(all_attributes)
    
    @property
    def overall_confidence(self) -> float:
        """Calculate overall confidence considering both Excel and LLM confidence."""
        if self.has_excel_data:
            # Weight Excel confidence higher
            return (self.excel_confidence * 0.7) + (self.llm_confidence * 0.3)
        else:
            return self.llm_confidence
    
    def normalize_fuel_type(self) -> Optional[str]:
        """Normalize fuel type to standard format."""
        if not self.fuel_type:
            return None
        
        fuel_mappings = {
            'DIESEL': 'DIESEL',
            'TD': 'DIESEL',
            'TDI': 'DIESEL',
            'GASOLINA': 'GASOLINE',
            'GASOLINE': 'GASOLINE',
            'GAS': 'GASOLINE',
            'NAFTA': 'GASOLINE',
            'ELECTRIC': 'ELECTRIC',
            'ELECTRICO': 'ELECTRIC',
            'HYBRID': 'HYBRID',
            'HIBRIDO': 'HYBRID'
        }
        
        return fuel_mappings.get(self.fuel_type.upper(), self.fuel_type)
    
    def normalize_drivetrain(self) -> Optional[str]:
        """Normalize drivetrain to standard format."""
        if not self.drivetrain:
            return None
        
        drivetrain_mappings = {
            '4X4': '4X4',
            '4WD': '4X4',
            'AWD': 'AWD',
            '4X2': '4X2',
            '2WD': '4X2',
            'FWD': 'FWD',
            'RWD': 'RWD'
        }
        
        return drivetrain_mappings.get(self.drivetrain.upper(), self.drivetrain)
    
    def normalize_body_style(self) -> Optional[str]:
        """Normalize body style to standard format."""
        if not self.body_style:
            return None
        
        body_mappings = {
            'DC': 'DOUBLE_CAB',
            'DOBLE CABINA': 'DOUBLE_CAB',
            'DOUBLE CAB': 'DOUBLE_CAB',
            'SC': 'SINGLE_CAB',
            'CABINA SIMPLE': 'SINGLE_CAB',
            'SINGLE CAB': 'SINGLE_CAB',
            'SEDAN': 'SEDAN',
            '4P': 'SEDAN',
            '4 PUERTAS': 'SEDAN',
            'SUV': 'SUV',
            'SPORT UTILITY': 'SUV',
            'HATCHBACK': 'HATCHBACK',
            '5P': 'HATCHBACK',
            'PICKUP': 'PICKUP',
            'PICK UP': 'PICKUP',
            'CAMIONETA': 'PICKUP'
        }
        
        return body_mappings.get(self.body_style.upper(), self.body_style)
    
    def matches_fuel_type(self, target_fuel: str) -> bool:
        """Check if fuel type matches target (with normalization)."""
        if not self.fuel_type or not target_fuel:
            return False
        
        normalized_self = self.normalize_fuel_type()
        normalized_target = VehicleAttributes(fuel_type=target_fuel).normalize_fuel_type()
        
        return normalized_self == normalized_target
    
    def matches_drivetrain(self, target_drivetrain: str) -> bool:
        """Check if drivetrain matches target (with normalization)."""
        if not self.drivetrain or not target_drivetrain:
            return False
        
        normalized_self = self.normalize_drivetrain()
        normalized_target = VehicleAttributes(drivetrain=target_drivetrain).normalize_drivetrain()
        
        return normalized_self == normalized_target
    
    def matches_body_style(self, target_body: str) -> bool:
        """Check if body style matches target (with normalization)."""
        if not self.body_style or not target_body:
            return False
        
        normalized_self = self.normalize_body_style()
        normalized_target = VehicleAttributes(body_style=target_body).normalize_body_style()
        
        return normalized_self == normalized_target
    
    def merge_with(self, other: 'VehicleAttributes') -> 'VehicleAttributes':
        """Merge with another VehicleAttributes, preferring non-null values from other."""
        return VehicleAttributes(
            brand=other.brand or self.brand,
            model=other.model or self.model,
            year=other.year or self.year,
            vin=other.vin or self.vin,
            coverage_package=other.coverage_package or self.coverage_package,
            fuel_type=other.fuel_type or self.fuel_type,
            drivetrain=other.drivetrain or self.drivetrain,
            body_style=other.body_style or self.body_style,
            trim_level=other.trim_level or self.trim_level,
            engine_size=other.engine_size or self.engine_size,
            transmission=other.transmission or self.transmission,
            doors=other.doors or self.doors,
            excel_confidence=max(self.excel_confidence, other.excel_confidence),
            llm_confidence=max(self.llm_confidence, other.llm_confidence)
        )
    
    def __str__(self) -> str:
        """Human readable representation."""
        parts = []
        if self.brand:
            parts.append(self.brand)
        if self.model:
            parts.append(self.model)
        if self.year:
            parts.append(str(self.year))
        
        return f"VehicleAttributes({' '.join(parts) if parts else 'empty'})"