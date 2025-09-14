import unicodedata
import re
import string
import pandas as pd

def deburr(s: str) -> str:
    """
    Remove diacritics (accents) from text.
    
    Args:
        s: Input string
        
    Returns:
        String with diacritics removed
    """
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def apply_norm(series: pd.Series, ops: str) -> pd.Series:
    """
    Apply normalization operations to a pandas Series.
    
    Args:
        series: Input pandas Series
        ops: Comma-separated list of operations (strip, lower, deburr)
        
    Returns:
        Normalized pandas Series
    """
    ops = [o.strip() for o in ops.split(",")]
    s = series.astype(str)
    
    if "strip" in ops:
        s = s.str.strip()
    if "lower" in ops:
        s = s.str.lower()
    if "deburr" in ops:
        s = s.map(deburr)
        
    return s

def render_expr(expr: str, row: dict) -> str:
    """
    Render an expression template with row data.
    
    Supports templates like "{brand} {model} {year}"
    
    Args:
        expr: Template expression
        row: Dictionary with row data
        
    Returns:
        Rendered string
    """
    # Replace {var} with ${var} for string.Template
    t = string.Template(expr.replace("{", "${"))
    
    # Substitute with safe handling of None values
    return t.safe_substitute({k: "" if v is None else str(v) for k, v in row.items()})