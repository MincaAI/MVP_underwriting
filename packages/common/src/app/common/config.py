from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # S3/Storage
    s3_endpoint_url: str
    s3_bucket_raw: str = "raw"
    s3_bucket_exports: str = "exports"
    s3_region: str = "us-east-1"
    aws_access_key_id: str
    aws_secret_access_key: str
    
    # SQS
    extractor_queue: str = "mincaai-extractor"
    codifier_queue: str = "mincaai-codifier"
    transform_queue: str = "mincaai-transform"
    exporter_queue: str = "mincaai-exporter"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # ML
    auto_accept_threshold: float = 0.85
    review_threshold: float = 0.70

    # Embedding Configuration
    embedding_model: str
    embedding_dimension: int
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-2-v2"

    # Matching Thresholds
    similarity_threshold: float
    fuzzy_match_threshold: float

    # Blend Weights
    w_embed: float
    w_fuzzy: float

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1

    # Service Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    vehicle_codifier_host: str = "0.0.0.0"
    vehicle_codifier_port: int = 8002
    smart_intake_host: str = "0.0.0.0"
    smart_intake_port: int = 8003

    # Azure Configuration
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None

    # Auth
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Feature Flags
    enable_auto_codify: bool = True
    enable_batch_processing: bool = True
    enable_audit_logging: bool = True
    
    # Environment
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    class Config:
        # Find project root and construct path to env file
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        env_file = project_root / "configs" / "env" / ".env.development"
        case_sensitive = False

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings