from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class VehicleInput(BaseModel):
    """Enhanced input model for vehicle description matching with Excel support."""
    
    # Primary fields
    description: str = Field(
        ..., 
        description="Vehicle description to match",
        example="L200 DIESEL 4X4 DC"
    )
    insurer_id: str = Field(
        "default",
        description="Insurer identifier for dataset selection"
    )
    
    # Excel pre-extracted fields (high confidence)
    brand: Optional[str] = Field(
        None,
        description="Brand from Excel Marca column",
        example="MITSUBISHI"
    )
    model: Optional[str] = Field(
        None,
        description="Model from Excel Submarka column",
        example="L200"
    )
    year: Optional[int] = Field(
        None,
        description="Year from Excel Ano MOdelos column",
        ge=1900,
        le=2030,
        example=2018
    )
    vin: Optional[str] = Field(
        None,
        description="VIN from Excel SERIE column",
        example="ML32A4HJ8JH123456"
    )
    coverage_package: Optional[str] = Field(
        None,
        description="Coverage package from Excel Paquete De Cobert column",
        example="BASICO"
    )
    
    # Metadata
    source_row: Optional[int] = Field(
        None,
        description="Source row number for tracking"
    )
    
    @validator('description')
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()
    
    @validator('brand', 'model')
    def normalize_text_fields(cls, v):
        if v:
            return v.strip().upper()
        return v
    
    @validator('vin')
    def normalize_vin(cls, v):
        if v:
            return v.strip().upper().replace(' ', '')
        return v


class VehicleAttributes(BaseModel):
    """Enhanced vehicle attributes with Excel and LLM extraction support."""
    
    # Core attributes (from Excel - high confidence)
    brand: Optional[str] = Field(None, description="Vehicle brand/manufacturer")
    model: Optional[str] = Field(None, description="Vehicle model/submarca")
    year: Optional[int] = Field(None, description="Model year")
    vin: Optional[str] = Field(None, description="Vehicle VIN/serial number")
    coverage_package: Optional[str] = Field(None, description="Coverage package")
    
    # Enhanced attributes (from LLM extraction - medium confidence)
    fuel_type: Optional[str] = Field(None, description="Fuel type (DIESEL, GASOLINA, etc.)")
    drivetrain: Optional[str] = Field(None, description="Drivetrain (4X4, 4X2, etc.)")
    body_style: Optional[str] = Field(None, description="Body style (DOUBLE_CAB, SEDAN, etc.)")
    trim_level: Optional[str] = Field(None, description="Trim level or package (DENALI, PREMIUM, etc.)")
    
    # Additional attributes
    engine_size: Optional[str] = Field(None, description="Engine size or displacement")
    transmission: Optional[str] = Field(None, description="Transmission type (MANUAL, AUTOMATICO)")
    doors: Optional[int] = Field(None, description="Number of doors")
    
    # Confidence tracking
    excel_confidence: float = Field(0.95, description="Confidence for Excel-extracted fields")
    llm_confidence: Optional[float] = Field(None, description="Confidence for LLM-extracted fields")
    
    model_config = {
        "json_encoders": {
            # Custom encoders if needed
        }
    }


class MatchConfidence(str, Enum):
    """Match confidence levels."""
    HIGH = "high"      # > 0.9
    MEDIUM = "medium"  # 0.7 - 0.9
    LOW = "low"        # 0.5 - 0.7
    VERY_LOW = "very_low"  # < 0.5


class MatchResult(BaseModel):
    """Enhanced result of vehicle matching process."""
    
    # Match information
    cvegs_code: str = Field(..., description="Matched CVEGS code")
    confidence_score: float = Field(
        ..., 
        description="Confidence score (0.0 - 1.0)",
        ge=0.0,
        le=1.0
    )
    confidence_level: MatchConfidence = Field(..., description="Confidence level category")
    
    # Matched vehicle details
    matched_brand: str = Field(..., description="Matched brand from dataset")
    matched_model: str = Field(..., description="Matched model from dataset")
    matched_year: Optional[int] = Field(None, description="Matched year")
    matched_description: str = Field(..., description="Full matched description from dataset")
    
    # Extraction details
    extracted_attributes: VehicleAttributes = Field(..., description="Attributes extracted from input")
    
    # Processing metadata
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    candidates_evaluated: int = Field(..., description="Number of candidates evaluated")
    match_method: str = Field(..., description="Method used for matching")
    
    # Enhanced matching details
    attribute_matches: Optional[Dict[str, bool]] = Field(
        None, 
        description="Detailed attribute match breakdown"
    )
    tie_breaker_used: bool = Field(
        False, 
        description="Whether LLM tie-breaker was used"
    )
    
    # Source tracking
    source_row: Optional[int] = Field(None, description="Source Excel row number")
    
    # Warnings or notes
    warnings: List[str] = Field(default_factory=list, description="Any warnings or notes")
    
    @validator('confidence_level', pre=True, always=True)
    def set_confidence_level(cls, v, values):
        if 'confidence_score' in values:
            score = values['confidence_score']
            if score >= 0.9:
                return MatchConfidence.HIGH
            elif score >= 0.7:
                return MatchConfidence.MEDIUM
            elif score >= 0.5:
                return MatchConfidence.LOW
            else:
                return MatchConfidence.VERY_LOW
        return v


class BatchMatchRequest(BaseModel):
    """Request model for batch vehicle matching."""
    
    vehicles: List[VehicleInput] = Field(
        ...,
        description="List of vehicles to match",
        max_items=200
    )
    insurer_id: str = Field(
        "default",
        description="Insurer identifier for dataset selection"
    )
    parallel_processing: bool = Field(
        True,
        description="Enable parallel processing"
    )
    
    @validator('vehicles')
    def vehicles_not_empty(cls, v):
        if not v:
            raise ValueError('Vehicles list cannot be empty')
        if len(v) > 200:
            raise ValueError('Maximum 200 vehicles allowed per batch')
        return v


class BatchMatchResponse(BaseModel):
    """Response model for batch vehicle matching."""
    
    results: List[MatchResult] = Field(..., description="Match results for each vehicle")
    summary: Dict[str, Any] = Field(..., description="Batch processing summary")
    total_processing_time_ms: float = Field(..., description="Total processing time")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "cvegs_code": "12345",
                        "confidence_score": 0.95,
                        "confidence_level": "high",
                        "matched_brand": "TOYOTA",
                        "matched_model": "YARIS",
                        "matched_description": "YARIS SOL L",
                        "extracted_attributes": {
                            "brand": "TOYOTA",
                            "model": "YARIS",
                            "year": 2020
                        },
                        "processing_time_ms": 150.5,
                        "candidates_evaluated": 5,
                        "match_method": "semantic_similarity",
                        "warnings": []
                    }
                ],
                "summary": {
                    "total_vehicles": 1,
                    "successful_matches": 1,
                    "high_confidence": 1,
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "failed_matches": 0
                },
                "total_processing_time_ms": 200.0
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")
    dataset_loaded: bool = Field(..., description="Whether CVEGS dataset is loaded")
    dataset_records: int = Field(..., description="Number of records in dataset")
    openai_available: bool = Field(..., description="Whether OpenAI API is available")
    redis_available: bool = Field(..., description="Whether Redis is available")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "1.0.0",
                "dataset_loaded": True,
                "dataset_records": 15000,
                "openai_available": True,
                "redis_available": True
            }
        }
    }
