from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class SmartIntakeSettings(BaseSettings):
    """Smart Intake Service configuration settings."""
    
    # Application Configuration
    app_name: str = "Smart Intake Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8002
    
    # Microsoft Graph Configuration
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    azure_redirect_uri: str = "https://api.yourdomain.com/oauth/callback"
    
    # Microsoft Graph API settings
    graph_api_base_url: str = "https://graph.microsoft.com/v1.0"
    graph_scopes: List[str] = ["Mail.Read", "MailboxSettings.Read", "offline_access"]
    
    # Webhook Configuration
    webhook_base_url: str = "https://api.yourdomain.com"
    webhook_validation_token: Optional[str] = None
    subscription_expiration_hours: int = 72  # Max 3 days for messages
    
    # Target folder configuration
    target_folder_name: str = "Fleet Auto"
    target_folder_id: Optional[str] = None  # Will be discovered if not provided
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/insurance_db"
    
    # OpenAI Configuration (for document intelligence)
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.1
    
    # File Storage Configuration
    storage_type: str = "local"  # local, s3, azure_blob
    local_storage_path: str = "storage"
    s3_bucket_name: Optional[str] = None
    s3_region: str = "us-east-1"
    
    # Processing Configuration
    max_attachment_size_mb: int = 50
    supported_mime_types: List[str] = [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/pdf",
        "image/jpeg",
        "image/png",
        "text/plain"
    ]
    
    # Document Intelligence Configuration
    max_pdf_pages: int = 50
    ocr_language: str = "spa"  # Spanish
    excel_max_sheets: int = 10
    
    # Service Integration URLs
    vehicle_matcher_url: str = "http://vehicle-matcher:8000"
    database_service_url: str = "http://database-service:8001"
    
    # Processing Timeouts
    email_processing_timeout: int = 300  # 5 minutes
    document_processing_timeout: int = 600  # 10 minutes
    vehicle_matching_timeout: int = 180  # 3 minutes
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    exponential_backoff: bool = True
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Security Configuration
    webhook_secret: Optional[str] = None  # For webhook signature validation
    internal_api_key: Optional[str] = None  # For service-to-service auth
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instances
settings = SmartIntakeSettings()


def get_settings() -> SmartIntakeSettings:
    """Get smart intake settings."""
    return settings


def get_graph_authority_url() -> str:
    """Get Microsoft Graph authority URL."""
    return f"https://login.microsoftonline.com/{settings.azure_tenant_id}"


def get_webhook_notification_url() -> str:
    """Get webhook notification URL for Graph subscriptions."""
    return f"{settings.webhook_base_url}/graph/notifications"


def get_oauth_callback_url() -> str:
    """Get OAuth callback URL."""
    return f"{settings.webhook_base_url}/oauth/callback"
