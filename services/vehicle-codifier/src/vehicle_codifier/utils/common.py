"""General utility functions."""

import re
from typing import Any
from unidecode import unidecode


def norm(text: str) -> str:
    """Normalize text for consistent processing (updated to lowercase)."""
    if not text:
        return ""
    return unidecode(str(text).strip().lower())


def normalize_text(text: Any) -> str:
    """
    Comprehensive text normalization for vehicle data with VIN removal.

    This is the new standardized normalization function that:
    - Uses lowercase for consistency across the project
    - Removes VIN patterns automatically
    - Handles unidecode transformation
    - Normalizes whitespace

    Args:
        text: Input text to normalize (any type, will be converted to string)

    Returns:
        Normalized lowercase text with VINs removed
    """
    if not text:
        return ""

    # Convert to string and basic cleaning
    cleaned = str(text).strip()

    # Remove VIN patterns (17-character alphanumeric, excludes I, O, Q)
    # This pattern matches VIN standards used in North America
    vin_pattern = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    cleaned = re.sub(vin_pattern, '', cleaned)

    # Remove extra whitespace and normalize spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Apply unidecode transformation and convert to lowercase
    # unidecode removes accents and converts unicode to ASCII
    return unidecode(cleaned).lower()


def normalize_catalog_field(field_value: Any) -> str:
    """
    Normalize catalog field values for consistent storage and matching.

    This function is specifically designed for AMIS catalog fields like
    marca, submarca, descveh, cvesegm, tipveh etc.

    Args:
        field_value: Field value from catalog (any type)

    Returns:
        Normalized text suitable for catalog storage and embeddings
    """
    return normalize_text(field_value)


# Legacy compatibility - keep old function but mark as deprecated
def norm_legacy(text: str) -> str:
    """
    Legacy normalization function (uppercase).

    DEPRECATED: Use normalize_text() instead for new code.
    This function is kept for backward compatibility only.
    """
    return norm(text)