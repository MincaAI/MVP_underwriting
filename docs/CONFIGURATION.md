# Configuration Guide

This document outlines the configuration setup for the MVP Underwriting project across different environments.

## Environment Configuration Files

### Development
- **Config**: `configs/app/development.yaml`
- **Environment**: `.env`
- **Database**: PostgreSQL with pgvector (Docker)
- **Storage**: MinIO (Docker)

### Staging
- **Config**: `configs/app/staging.yaml`
- **Environment**: `configs/env/staging.env`
- **Database**: AWS RDS PostgreSQL with pgvector
- **Storage**: AWS S3

### Production
- **Config**: `configs/app/production.yaml`
- **Environment**: `configs/env/production.env`
- **Database**: AWS RDS PostgreSQL with pgvector
- **Storage**: AWS S3

## Standardized Configuration

### Database Configuration
```yaml
# Consistent across all environments
database:
  host: localhost (dev) | ${DB_HOST} (staging/prod)
  port: 5432
  name: minca
  user: minca
  password: minca (dev) | ${DB_PASSWORD} (staging/prod)
```

### Storage Configuration
```yaml
# Development (MinIO)
storage:
  provider: minio
  endpoint: http://localhost:9000
  access_key: minio
  secret_key: minio12345
  bucket_raw: raw
  bucket_exports: exports

# Staging/Production (AWS S3)
storage:
  provider: s3
  endpoint: https://s3.${AWS_REGION}.amazonaws.com
  access_key: ${AWS_ACCESS_KEY_ID}
  secret_key: ${AWS_SECRET_ACCESS_KEY}
  bucket_raw: ${S3_BUCKET_RAW}
  bucket_exports: ${S3_BUCKET_EXPORTS}
```

## Package Dependencies

The API service includes the following workspace packages that are automatically managed by Poetry:

- **`db`**: Database models and session management
  - SQLAlchemy models for cases, emails, attachments, runs
  - Database session management and connection pooling
  - Alembic migrations support

- **`storage`**: S3/MinIO storage utilities
  - File upload and download functionality
  - S3-compatible storage abstraction
  - Support for both local MinIO and AWS S3

- **`schemas`**: Pydantic schemas and data models
  - Request/response validation schemas
  - Data transformation models
  - Type-safe API contracts

- **`mincaai-mq`**: Message queue utilities
  - Local in-memory queue for development
  - SQS integration for production
  - Async message processing support

All packages are installed as editable dependencies when running `poetry install` in the API service directory.

## Environment Variables

### Required Variables
```bash
# Database
POSTGRES_DB=minca
POSTGRES_USER=minca
POSTGRES_PASSWORD=minca
DATABASE_URL=postgresql+psycopg://minca:minca@localhost:5432/minca

# Storage
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=minio12345
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_RAW=raw
S3_BUCKET_EXPORTS=exports

# External Services
OPENAI_API_KEY=your_openai_api_key_here

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
JWT_SECRET=dev-secret-change-in-production
```

## Setup Instructions

### Local Development
1. Copy `.env.example` to `.env`
2. Update values as needed
3. Start services: `docker compose up -d db minio`
4. Run API: `cd services/api && ./run_local.sh`

**Alternative API startup methods:**
```bash
# Method 1: Using the shell script (recommended)
./run_local.sh

# Method 2: Using the Python launcher
python run_api.py

# Method 3: Direct uvicorn command
poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Staging/Production
1. Copy environment template from `configs/env/`
2. Update with actual AWS credentials and endpoints
3. Deploy using Terraform infrastructure
4. Configure environment variables in deployment system

## Configuration Validation

The API health endpoint (`/health`) now shows:
- Database connection status
- S3/MinIO connection status
- MinIO credentials status
- Bucket configuration status

## Troubleshooting

### Common Issues
1. **Environment variables not loading**: Ensure `.env` file is in project root
2. **Database connection failed**: Check PostgreSQL is running and credentials match
3. **S3/MinIO connection failed**: Verify endpoint URL and credentials
4. **Bucket not found**: Ensure buckets are created in MinIO/S3

### Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "ok": true,
  "db": "postgresql+psycopg://minca:minca@localhost:5432/minca",
  "s3": "http://localhost:9000",
  "minio_user": "minio",
  "minio_password": "***",
  "s3_bucket_raw": "raw",
  "s3_bucket_exports": "exports"
}
```
