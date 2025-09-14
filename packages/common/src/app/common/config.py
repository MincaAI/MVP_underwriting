from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg://minca:minca@localhost:5432/minca"
    
    # S3/Storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket_raw: str = "raw"
    s3_bucket_exports: str = "exports"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = "minio"
    aws_secret_access_key: str = "minio12345"
    
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
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-2-v2"
    
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
        env_file = ".env"
        case_sensitive = False

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings