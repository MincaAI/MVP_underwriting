"""Vehicle domain entity representing a vehicle to be matched."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from ..value_objects.vehicle_attributes import VehicleAttributes


@dataclass(frozen=True)
class Vehicle:
    """Core vehicle entity with immutable properties."""
    
    # Core identification
    description: str
    insurer_id: str
    
    # Excel pre-extracted data (high confidence)
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vin: Optional[str] = None
    coverage_package: Optional[str] = None
    
    # Metadata
    source_row: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate entity invariants."""
        if not self.description or not self.description.strip():
            raise ValueError("Vehicle description cannot be empty")
        
        if not self.insurer_id or not self.insurer_id.strip():
            raise ValueError("Insurer ID cannot be empty")
        
        if self.year is not None and (self.year < 1900 or self.year > 2030):
            raise ValueError(f"Invalid year: {self.year}")
    
    @property
    def has_excel_data(self) -> bool:
        """Check if vehicle has any Excel pre-extracted data."""
        return any([self.brand, self.model, self.year, self.vin, self.coverage_package])
    
    @property
    def excel_completeness(self) -> float:
        """Calculate completeness of Excel data (0.0 to 1.0)."""
        excel_fields = [self.brand, self.model, self.year, self.vin, self.coverage_package]
        filled_fields = sum(1 for field in excel_fields if field is not None)
        return filled_fields / len(excel_fields)
    
    def to_attributes(self) -> VehicleAttributes:
        """Convert to VehicleAttributes value object."""
        return VehicleAttributes(
            brand=self.brand,
            model=self.model,
            year=self.year,
            vin=self.vin,
            coverage_package=self.coverage_package,
            fuel_type=None,  # Will be extracted later
            drivetrain=None,  # Will be extracted later
            body_style=None,  # Will be extracted later
            trim_level=None,  # Will be extracted later
            engine_size=None,  # Will be extracted later
            transmission=None,  # Will be extracted later
            doors=None,  # Will be extracted later
            excel_confidence=0.95 if self.has_excel_data else 0.0
        )
    
    @classmethod
    def from_input(cls, 
                   description: str,
                   insurer_id: str,
                   brand: Optional[str] = None,
                   model: Optional[str] = None,
                   year: Optional[int] = None,
                   vin: Optional[str] = None,
                   coverage_package: Optional[str] = None,
                   source_row: Optional[int] = None) -> 'Vehicle':
        """Create Vehicle from input parameters."""
        return cls(
            description=description.strip(),
            insurer_id=insurer_id.strip(),
            brand=brand.upper().strip() if brand else None,
            model=model.upper().strip() if model else None,
            year=year,
            vin=vin.upper().strip().replace(' ', '') if vin else None,
            coverage_package=coverage_package.upper().strip() if coverage_package else None,
            source_row=source_row,
            created_at=datetime.utcnow()
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
        
        if parts:
            return f"Vehicle({' '.join(parts)})"
        else:
            return f"Vehicle({self.description[:30]}...)"