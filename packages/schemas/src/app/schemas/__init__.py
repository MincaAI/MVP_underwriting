"""
Canonical Pydantic schemas for Minca AI Insurance Platform.

This package contains all the core data models used across services for:
- Data validation and serialization
- API contracts
- Inter-service communication
- Database schema validation
"""

from .core import (
    CanonicalVehicleRow,
    Candidate,
    CodifyResult,
    ExportSummary,
)

from .vehicle import (
    CanonicalVehicle,
    ValuationType,
    FuelType,
    UseType,
    Coverage,
    FIELD_SYNONYMS,
)

__version__ = "0.1.0"

__all__ = [
    # Core schemas
    "CanonicalVehicleRow",
    "Candidate", 
    "CodifyResult",
    "ExportSummary",
    # Vehicle schemas
    "CanonicalVehicle",
    "ValuationType",
    "FuelType", 
    "UseType",
    "Coverage",
    "FIELD_SYNONYMS",
]