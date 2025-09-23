"""Configuration for the simplified vehicle codifier service."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from pydantic_settings import BaseSettings

# Add the common package to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "packages" / "common" / "src"))

try:
    from app.common.config import get_settings as get_common_settings
    COMMON_CONFIG_AVAILABLE = True
except ImportError:
    COMMON_CONFIG_AVAILABLE = False


class Settings(BaseSettings):
    """Application settings."""

    # Service info
    app_name: str = "Vehicle Codifier Service"
    app_version: str = "0.2.0-simplified"
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+psycopg://minca:minca@localhost:5432/minca"

    # OpenAI for field extraction - will fallback to common config
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # Embedding model (must match catalog embedding model)
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dimension: int = 1024

    # Decision thresholds (default for passenger cars)
    threshold_high: float = 0.90  # auto_accept
    threshold_low: float = 0.70   # needs_review (below this = no_match)

    # Dynamic thresholds by vehicle type
    thresholds_by_type: Dict[str, Dict[str, float]] = {
        "auto": {"high": 0.90, "low": 0.70},           # Passenger cars
        "camioneta": {"high": 0.75, "low": 0.55},      # Commercial trucks/tractors
        "motocicleta": {"high": 0.85, "low": 0.65},    # Motorcycles
        "default": {"high": 0.80, "low": 0.60}         # Other vehicle types
    }

    # Enhanced reranking weights (must sum to 1.0) - optimized for trusted year input
    weight_embedding: float = 0.40      # Embedding similarity
    weight_fuzzy: float = 0.20          # Fuzzy text matching
    weight_brand_match: float = 0.10    # Brand exact match bonus
    weight_year_proximity: float = 0.25 # Year proximity bonus (high weight for trusted year)
    weight_type_match: float = 0.05     # Vehicle type match bonus

    # Query limits
    max_candidates: int = 25
    max_results: int = 5

    # Embedding-first approach settings
    embedding_only_candidates: int = 20  # Get top 20 by embedding similarity only
    semantic_search_threshold: int = 20  # Skip embedding search if pre-filtered candidates <= this number
    reranker_threshold: int = 20  # Use LLM reranker if candidates >= this number

    # Enhanced response options
    return_candidates_on_no_match: bool = True
    min_candidates_for_review: int = 3
    max_candidates_for_review: int = 5

    # Year range for vehicle detection
    min_vehicle_year: int = 1950
    future_years_ahead: int = 5
    year_variance: int = 0  # Exact year matching only

    # Catalog caching
    cache_enabled: bool = True
    cache_refresh_interval_hours: int = 24
    cache_preload_on_startup: bool = True
    cache_max_memory_mb: int = 500

    # Brand filtering for candidate reduction
    enable_brand_filtering: bool = True
    brand_filter_confidence_threshold: float = 0.8

    # Debug information
    enable_debug_filtering: bool = True

    # High-confidence filtering threshold
    high_confidence_threshold: float = 0.9

    # Dynamic filtering system (always enabled)
    dynamic_filter_order: List[str] = ["marca", "submarca", "tipveh"]
    filter_confidence_thresholds: Dict[str, Dict[str, float]] = {
        "marca": {"high": 0.8, "skip": 0.4},
        "submarca": {"high": 0.7, "skip": 0.3},
        "tipveh": {"high": 0.6, "skip": 0.2}
    }
    max_candidates_before_filtering: int = 100
    min_candidates_after_filtering: int = 5
    use_llm_fallback: bool = True

    # Submarca validation patterns
    submarca_validation: Dict[str, Any] = {
        "min_length": 2,
        "max_length": 25,
        "excluded_patterns": [
            r"^[A-HJ-NPR-Z0-9]{17}$",  # VIN pattern (17 chars, excludes I, O, Q)
            r"^[A-Z0-9]{10,20}$",      # License plate/serial patterns
            r"^\d{4,}$",               # Pure numeric sequences (4+ digits)
            r"^[A-Z]{1,2}\d{4,}$"      # Pattern like "A1234" or "AB1234"
        ]
    }

    class Config:
        # Find project root and construct path to env file
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / "configs" / "env" / ".env.development"
        extra = "ignore"  # Allow extra environment variables to be ignored


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()