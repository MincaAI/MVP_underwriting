from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
# from .routes_codify import router as codify_router
# from .routes_transform import router as transform_router
# from .routes_export import router as export_router
from .routes_email import router as email_router
from .routes_upload import router as upload_router
from .routes_processing import router as processing_router

# Load environment variables
load_dotenv()

# Detect if we're running in Docker or locally
def is_docker_environment():
    """Check if we're running in Docker container"""
    return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'

# Only apply local development fixes if NOT running in Docker
if not is_docker_environment():
    # Fix S3 endpoint and credentials for local development
    if os.getenv("S3_ENDPOINT_URL") == "http://minio:9000":
        # Running locally, use localhost instead of Docker internal URL
        os.environ["S3_ENDPOINT_URL"] = "http://localhost:9000"

    # Set AWS credentials from MinIO credentials for local development
    if not os.getenv("AWS_ACCESS_KEY_ID"):
        os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("MINIO_ROOT_USER", "minio")
    if not os.getenv("AWS_SECRET_ACCESS_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("MINIO_ROOT_PASSWORD", "minio12345")

    # Fix database URL for local development
    if os.getenv("DATABASE_URL") and "db:5432" in os.getenv("DATABASE_URL"):
        # Running locally, use localhost instead of Docker internal URL
        os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL").replace("db:5432", "localhost:5432")

app = FastAPI(
    title="Minca API", 
    version="0.1.0",
    description="Simplified API for email processing and document preprocessing for vehicle matching"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# app.include_router(codify_router)
# app.include_router(transform_router)
# app.include_router(export_router)
app.include_router(email_router)
app.include_router(upload_router)
app.include_router(processing_router)  # New processing routes

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "Minca API - Simplified Preprocessing Pipeline",
        "version": "0.1.0",
        "db": os.getenv("DATABASE_URL", "unset"),
        "s3": os.getenv("S3_ENDPOINT_URL", "unset"),
        "minio_user": os.getenv("MINIO_ROOT_USER", "unset"),
        "minio_password": "***" if os.getenv("MINIO_ROOT_PASSWORD") else "unset",
        "s3_bucket_raw": os.getenv("S3_BUCKET_RAW", "unset"),
        "s3_bucket_exports": os.getenv("S3_BUCKET_EXPORTS", "unset"),
        "queue_backend": os.getenv("QUEUE_BACKEND", "local")
    }