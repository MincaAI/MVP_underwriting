"""Pydantic models for the vehicle codifier service."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, RootModel


class VehicleInput(BaseModel):
    """Input for vehicle matching."""
    modelo: int = Field(..., description="Year of the vehicle")
    description: str = Field(..., description="Vehicle description text")


class ExtractedFields(BaseModel):
    """Fields extracted from vehicle description."""
    marca: Optional[str] = None
    submarca: Optional[str] = None
    cvesegm: Optional[str] = None  # segment
    descveh: Optional[str] = None  # cleaned description
    tipveh: Optional[str] = None   # vehicle type


class FieldConfidence(BaseModel):
    """Confidence score for an extracted field."""
    value: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"  # "direct", "fuzzy", "keyword", "llm"


class ExtractedFieldsWithConfidence(BaseModel):
    """Fields extracted from vehicle description with confidence scores."""
    marca: FieldConfidence = Field(default_factory=FieldConfidence)
    submarca: FieldConfidence = Field(default_factory=FieldConfidence)
    cvesegm: FieldConfidence = Field(default_factory=FieldConfidence)
    descveh: Optional[str] = None  # cleaned description (always available)
    tipveh: FieldConfidence = Field(default_factory=FieldConfidence)

    def to_extracted_fields(self) -> ExtractedFields:
        """Convert to legacy ExtractedFields format."""
        return ExtractedFields(
            marca=self.marca.value,
            submarca=self.submarca.value,
            cvesegm=self.cvesegm.value,
            descveh=self.descveh,
            tipveh=self.tipveh.value
        )


class Candidate(BaseModel):
    """A matching candidate from the catalog."""
    cvegs: int
    marca: str
    submarca: str
    modelo: int
    descveh: str
    label: str
    similarity_score: float
    fuzzy_score: float
    final_score: float
    cvesegm: Optional[str] = None
    tipveh: Optional[str] = None


class ReviewCandidate(BaseModel):
    """A candidate suggestion for manual review."""
    cvegs: int
    marca: str
    submarca: str
    modelo: int
    descveh: str
    confidence: float
    match_quality: str  # "high", "medium", "low"
    similarity_score: float = 0.0
    fuzzy_score: float = 0.0


class MatchResult(BaseModel):
    """Result of vehicle matching."""
    success: bool
    decision: str  # auto_accept, needs_review, no_match
    confidence: float
    suggested_cvegs: Optional[int] = None
    candidates: List[Candidate] = []
    extracted_fields: Optional[ExtractedFields] = None
    processing_time_ms: float
    query_label: Optional[str] = None

    # Enhanced fields for better user experience
    top_candidates_for_review: List[ReviewCandidate] = []
    recommendation: Optional[str] = None  # "auto_accept", "manual_review_suggested", etc.

    # Debug information (optional)
    debug_info: Optional[Dict[str, Any]] = None


class FlexibleMatchRequest(RootModel[Dict[str, Dict[str, Any]]]):
    """Flexible matching request with numbered JSON object."""
    root: Dict[str, Dict[str, Any]]  # {"0": {...}, "1": {...}}


class FlexibleMatchResponse(BaseModel):
    """Flexible matching response with preserved row IDs."""
    results: Dict[str, MatchResult]  # {"0": result, "1": result}
    total_processed: int
    successful_matches: int
    processing_time_ms: float
    field_mappings: Dict[str, Dict[str, str]] = {}  # {"0": {"año": "modelo"}}
    errors: Dict[str, str] = {}  # {"2": "Missing year field"}


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database_connected: bool
    active_catalog_version: Optional[str] = None
    catalog_records: int = 0
    embedding_model: str