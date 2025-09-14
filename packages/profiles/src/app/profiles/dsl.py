from pydantic import BaseModel
from typing import Dict, List, Optional

class Mapping(BaseModel):
    """Column mapping and normalization configuration."""
    columns: Dict[str, str]            # input header -> canonical
    normalize: Dict[str, str] = {}     # e.g. brand: "lower, strip, deburr"

class Compute(BaseModel):
    """Computed column configuration."""
    add_columns: Dict[str, str] = {}   # new_col: "concat({brand}, ' ', {model})"

class Validate(BaseModel):
    """Validation rules for transformed data."""
    required: List[str] = []
    ranges: Dict[str, Dict[str, int]] = {}  # year: {min:1990,max:2100}
    enums: Dict[str, List[str]] = {}        # use: ["comercial","carga"]

class Profile(BaseModel):
    """Complete broker profile configuration."""
    detect: Dict[str, object] = {}     # sheet_regex, required_headers
    mapping: Mapping
    compute: Optional[Compute] = None
    validate: Optional[Validate] = None