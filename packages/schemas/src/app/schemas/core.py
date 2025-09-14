from typing import List, Optional, Literal
from pydantic import BaseModel, Field, constr, conint, confloat

# --- Canonical row we pass around after extraction/transform ---
class CanonicalVehicleRow(BaseModel):
    case_id: str = Field(..., description="Case this row belongs to (UUID)")
    row_idx: int = Field(..., ge=0, description="Row index within the source file")
    brand: constr(strip_whitespace=True, to_lower=True) = Field(..., description="Marca")
    model: constr(strip_whitespace=True) = Field(..., description="Submarca/Modelo")
    year: conint(ge=1950, le=2100) = Field(..., description="Año")
    body: Optional[str] = Field(None, description="Carrocería / body style")
    use:  Optional[str] = Field(None, description="Uso (carga/pasajeros/comercial)")
    # Original free text for reference/debugging
    description: Optional[str] = Field(None, description="Original vehicle description text")
    # Anything else we keep (plate, serie, etc.)
    extra: dict = Field(default_factory=dict)

# --- Codifier output per row ---
class Candidate(BaseModel):
    cvegs: str
    label: str
    score: confloat(ge=0, le=1)

class CodifyResult(BaseModel):
    case_id: str
    row_idx: int
    suggested_cvegs: Optional[str] = None
    confidence: confloat(ge=0, le=1) = 0.0
    candidates: List[Candidate] = Field(default_factory=list)
    decision: Literal["auto_accept", "needs_review", "no_match"]

# --- Export summary we show after building the Gcotiza.xlsx ---
class ExportSummary(BaseModel):
    case_id: str
    run_id: str
    target: Literal["Gcotiza"]
    file_url: str
    checksum: str
    rows_total: int
    rows_auto_accepted: int
    rows_reviewed: int
    rows_unresolved: int