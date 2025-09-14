from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    app_name: str = "Vehicle Codifier Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1
    
    # Database Configuration
    database_url: Optional[str] = None
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_cache_ttl: int = 3600  # 1 hour
    
    # Data Configuration
    cvegs_dataset_path: str = "data/cvegs_dataset.xlsx"
    
    # Processing Configuration
    max_batch_size: int = 200
    max_concurrent_requests: int = 50
    request_timeout: int = 30
    
    # Matching Configuration
    confidence_threshold: float = 0.8
    max_candidates: int = 10
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Multi-insurer Configuration
    default_insurer: str = "default"
    insurer_configs_path: str = "config/insurers"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class InsurerConfig(BaseSettings):
    """Configuration for a specific insurer."""
    
    insurer_id: str
    insurer_name: str
    dataset_path: str
    
    # Column mapping for Spanish Excel headers
    column_mapping: Dict[str, str] = {
        "MARCA": "brand",
        "SUBMARCA": "model", 
        "MODELO": "year_code",
        "DESCVEH": "description",
        "CVEGS": "cvegs_code"
    }
    
    # Business rules
    confidence_threshold: float = 0.8
    max_candidates: int = 10
    
    # Year code mapping (if needed)
    year_code_mapping: Optional[Dict[str, int]] = None
    
    # Brand aliases for normalization
    brand_aliases: Dict[str, str] = {
        "GM": "GENERAL MOTORS",
        "GENERAL MOTORS": "GENERAL MOTORS",
        "TOYOTA": "TOYOTA",
        "MITSUBISHI": "MITSUBISHI"
    }


# Global settings instance
settings = Settings()


def get_insurer_config(insurer_id: str) -> InsurerConfig:
    """Get configuration for a specific insurer."""
    
    # Default configuration
    if insurer_id == "default":
        return InsurerConfig(
            insurer_id="default",
            insurer_name="Default Insurer",
            dataset_path=settings.cvegs_dataset_path
        )
    
    # Load from file or database in the future
    # For now, return default
    return InsurerConfig(
        insurer_id=insurer_id,
        insurer_name=f"Insurer {insurer_id}",
        dataset_path=f"data/{insurer_id}_cvegs_dataset.xlsx"
    )


def get_settings() -> Settings:
    """Get application settings."""
    return settings
