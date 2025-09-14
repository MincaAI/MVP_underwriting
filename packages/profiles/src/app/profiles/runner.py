import re
import pandas as pd
from typing import Tuple, Dict
from .dsl import Profile
from .utils import apply_norm, render_expr

def apply_profile(df: pd.DataFrame, profile: Profile) -> Tuple[pd.DataFrame, Dict]:
    """
    Apply a broker profile to transform raw data to canonical format.
    
    Args:
        df: Raw input DataFrame
        profile: Profile configuration
        
    Returns:
        Tuple of (transformed_df, report_dict)
    """
    out = df.copy()
    errors = {}
    
    # 1) Header normalization (lower/strip)
    out.columns = [c.strip().lower() for c in out.columns]
    
    # 2) Detection - check required headers exist
    req = profile.detect.get("required_headers", [])
    missing = [h for h in req if h not in out.columns]
    if missing:
        return out, {
            "errors": {"missing_headers": missing}, 
            "metrics": {"rows": len(out)}
        }
    
    # 3) Column mapping (rename input headers to canonical names)
    rename = {
        src.lower(): dst 
        for src, dst in profile.mapping.columns.items() 
        if src.lower() in out.columns
    }
    out = out.rename(columns=rename)
    
    # 4) Normalize fields according to rules
    for col, ops in (profile.mapping.normalize or {}).items():
        if col in out.columns:
            out[col] = apply_norm(out[col], ops)
    
    # 5) Compute new columns from expressions
    if profile.compute:
        for new_col, expr in (profile.compute.add_columns or {}).items():
            out[new_col] = out.apply(
                lambda r: render_expr(expr, r.to_dict()), 
                axis=1
            )
    
    # 6) Validation
    v_err = {}
    if profile.validate:
        # Check required canonical columns exist
        missing_canonical = [
            c for c in (profile.validate.required or []) 
            if c not in out.columns
        ]
        if missing_canonical:
            v_err["missing_canonical"] = missing_canonical
        
        # Range validation
        for col, rng in (profile.validate.ranges or {}).items():
            if col in out.columns:
                bad_indices = []
                
                # Check if values are numeric (4-digit years)
                non_numeric = out[~out[col].astype(str).str.fullmatch(r"\\d{4}")].index.tolist()
                bad_indices.extend(non_numeric)
                
                # Check minimum range
                if "min" in rng:
                    below_min = out[out[col].astype(float) < rng["min"]].index.tolist()
                    bad_indices.extend(below_min)
                
                # Check maximum range
                if "max" in rng:
                    above_max = out[out[col].astype(float) > rng["max"]].index.tolist()
                    bad_indices.extend(above_max)
                
                if bad_indices:
                    v_err[f"{col}_range"] = sorted(set(map(int, bad_indices)))
        
        # Enum validation
        for col, valid_vals in (profile.validate.enums or {}).items():
            if col in out.columns:
                invalid_indices = out[~out[col].isin(valid_vals)].index.tolist()
                if invalid_indices:
                    v_err[f"{col}_enum"] = invalid_indices
    
    # Build metrics
    metrics = {"rows": len(out)}
    if v_err:
        metrics["validation_errors"] = {
            k: len(v) if isinstance(v, list) else v 
            for k, v in v_err.items()
        }
    
    return out, {"errors": v_err, "metrics": metrics}