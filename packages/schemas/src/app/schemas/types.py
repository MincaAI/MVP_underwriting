from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Literal
from datetime import datetime
from enum import Enum

# Status Enums
class CaseStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class RunStatus(str, Enum):
    CREATED = "created"
    EXTRACTING = "extracting"
    CODIFYING = "codifying"
    TRANSFORMING = "transforming"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    ERROR = "error"

# Base Models
class BaseEntity(BaseModel):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

# Case Models
class Case(BaseEntity):
    filename: str
    file_type: str
    file_size: int
    s3_key: str
    status: CaseStatus
    user_id: str
    broker_profile: Optional[str] = None

class CaseCreate(BaseModel):
    filename: str
    file_type: str
    file_size: int
    s3_key: str
    user_id: str
    broker_profile: Optional[str] = None

# Run Models
class Run(BaseEntity):
    case_id: str
    status: RunStatus
    broker_profile: str
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None
    error_rows: Optional[int] = None
    metrics: Optional[Dict[str, Any]] = None

class RunCreate(BaseModel):
    case_id: str
    broker_profile: str

# Row Models (Canonical Schema)
class CanonicalRow(BaseModel):
    id: str
    case_id: str
    run_id: Optional[str] = None
    
    # Vehicle Information
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_vin: Optional[str] = None
    vehicle_value: Optional[float] = None
    
    # Coverage Information
    coverage_type: Optional[str] = None
    coverage_limit: Optional[str] = None
    coverage_deductible: Optional[str] = None
    
    # Broker/Client Information
    broker_name: Optional[str] = None
    client_name: Optional[str] = None
    policy_number: Optional[str] = None
    
    # Extracted raw data
    raw_data: Dict[str, Any]
    
    # Processing metadata
    extraction_confidence: Optional[float] = None
    needs_review: bool = False

# Codify Models
class CodifyResult(BaseModel):
    id: str
    row_id: str
    cvegs_code: Optional[str] = None
    confidence: float
    candidates: List[str] = []
    needs_review: bool
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

class CodifyCandidate(BaseModel):
    cvegs_code: str
    description: str
    score: float

# Transform Models
class TransformResult(BaseModel):
    id: str
    run_id: str
    transformed_data: List[Dict[str, Any]]
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    profile_version: str
    applied_rules: List[str] = []

# Export Models
class Export(BaseModel):
    id: str
    run_id: str
    format: Literal["Gcotiza", "CSV", "JSON"]
    s3_key: str
    row_count: int
    error_count: int
    warning_count: int
    exported_at: datetime
    exported_by: str

# AMIS Catalogue Models
class AmisEntry(BaseModel):
    cvegs_code: str
    description: str
    category: str
    subcategory: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    embedding: Optional[List[float]] = None

# API Request/Response Models
class IngestRequest(BaseModel):
    broker_profile: str

class IngestResponse(BaseModel):
    case_id: str
    message: str

class TransformRequest(BaseModel):
    case_id: str
    profile: str

class TransformResponse(BaseModel):
    run_id: str
    metrics: Dict[str, Any]

class PreviewResponse(BaseModel):
    run_id: str
    original_rows: List[Dict[str, Any]]
    transformed_rows: List[Dict[str, Any]]
    diffs: List[Dict[str, Any]]
    metrics: Dict[str, Any]

class CodifyBatchRequest(BaseModel):
    run_id: str
    row_ids: Optional[List[str]] = None

class CodifyBatchResponse(BaseModel):
    processed_count: int
    needs_review_count: int
    auto_accepted_count: int

class CodifyReviewRequest(BaseModel):
    run_id: str
    corrections: Dict[str, str]  # row_id -> cvegs_code

class ExportRequest(BaseModel):
    run_id: str
    target: Literal["Gcotiza", "CSV", "JSON"] = "Gcotiza"

class ExportResponse(BaseModel):
    download_url: str
    expires_at: datetime
    row_count: int
    warnings: List[str] = []

# Error Models
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class APIError(BaseModel):
    error: str
    details: List[ErrorDetail] = []
    trace_id: Optional[str] = None