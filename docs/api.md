# API Reference

## Overview

The Minca AI Insurance Processing Platform provides REST APIs across multiple services:

- **Main API** (`http://localhost:8000`): Orchestration, workflow management, email processing, and file uploads
- **Document Processor** (`http://localhost:8001`): Excel processing, transformation, and export  
- **Vehicle Codifier** (`http://localhost:8002`): AMIS/CVEGS vehicle matching and codification
- **Smart Intake** (`http://localhost:8002`): Email processing and broker profile management

## Package Dependencies

The API service includes the following workspace packages:
- `db`: Database models and session management
- `storage`: S3/MinIO storage utilities  
- `schemas`: Pydantic schemas and data models
- `mincaai-mq`: Message queue utilities for local and SQS backends

## Authentication

Currently, no authentication is required for development. Production will implement JWT-based authentication.

## Services

## Endpoints

### Health Check

#### GET /health

Check API and infrastructure status.

**Response:**
```json
{
  "ok": true,
  "db": "postgresql://...",
  "s3": "http://localhost:9000"
}
```

---

## Email Processing API

### POST /email/process-manual

Process manual email data with attachments and broker profile detection.

**Content-Type**: `multipart/form-data`

**Form Fields:**
- `from_email` (required): Email sender address
- `subject` (required): Email subject line  
- `received_date` (optional): Date email was received (ISO format)
- `content` (required): Email body content
- `attachments` (required): File attachments (Excel/CSV files)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/email/process-manual" \
  -F "from_email=broker@luckygas.com.mx" \
  -F "subject=Fleet Insurance Request - Acme Corp" \
  -F "content=Please find attached our vehicle list for insurance quote..." \
  -F "received_date=2024-09-15T14:30:22Z" \
  -F "attachments=@fleet_vehicles.xlsx"
```

**Response:**
```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Email processing started successfully",
  "attachments_processed": 1,
  "extract_messages_sent": 1
}
```

### GET /email/{email_id}

Get email message details by ID.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "from_email": "broker@luckygas.com.mx",
  "subject": "Fleet Insurance Request - Acme Corp",
  "content": "Please find attached our vehicle list...",
  "received_date": "2024-09-15T14:30:22Z",
  "case_id": "EMAIL_20240915_143022",
  "status": "processing"
}
```

---

## File Upload API

### POST /upload

Upload a single file for processing.

**Content-Type**: `multipart/form-data`

**Form Fields:**
- `file` (required): File to upload (Excel/CSV)
- `case_id` (optional): Case identifier (auto-generated if not provided)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@fleet_vehicles.xlsx" \
  -F "case_id=test-case-001"
```

**Response:**
```json
{
  "case_id": "test-case-001",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "fleet_vehicles.xlsx",
  "file_size": 245760,
  "s3_uri": "s3://raw/test-case-001/fleet_vehicles.xlsx",
  "status": "uploaded"
}
```

### POST /upload-multiple

Upload multiple files for batch processing.

**Content-Type**: `multipart/form-data`

**Form Fields:**
- `files` (required): Multiple files to upload
- `case_id` (optional): Case identifier (auto-generated if not provided)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/upload-multiple" \
  -F "files=@fleet_vehicles.xlsx" \
  -F "files=@additional_vehicles.csv" \
  -F "case_id=batch-case-001"
```

**Response:**
```json
{
  "case_id": "batch-case-001",
  "files_processed": 2,
  "runs": [
    {
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "file_name": "fleet_vehicles.xlsx",
      "s3_uri": "s3://raw/batch-case-001/fleet_vehicles.xlsx"
    },
    {
      "run_id": "550e8400-e29b-41d4-a716-446655440001", 
      "file_name": "additional_vehicles.csv",
      "s3_uri": "s3://raw/batch-case-001/additional_vehicles.csv"
    }
  ]
}
```

---

## Transform API

### POST /transform

Transform broker data using a profile configuration.

**Parameters:**
- `case_id` (required): Case identifier
- `s3_uri` (required): S3 URI of the source file (e.g., `s3://bucket/file.xlsx`)
- `profile` (optional): Profile path (default: `configs/broker-profiles/lucky_gas.yaml`)

**Response:**
```json
{
  "run_id": "uuid-v4"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/transform?case_id=test-case&s3_uri=s3://bucket/lucky_gas_fleet.xlsx&profile=lucky_gas.yaml"
```

### GET /transform/preview

Preview transformed data for a run.

**Parameters:**
- `run_id` (required): Transform run identifier
- `limit` (optional): Number of rows to preview (default: 10)

**Response:**
```json
{
  "run_id": "uuid",
  "status": "SUCCESS",
  "metrics": {
    "rows": 45,
    "validation_errors": {}
  },
  "preview": [
    {
      "row_idx": 0,
      "transformed": {
        "brand": "nissan",
        "model": "sentra",
        "year": 2020,
        "body": "sedan",
        "use": "particular",
        "description": "nissan sentra 2020 sedan particular"
      },
      "errors": {},
      "warnings": {}
    }
  ]
}
```

---

## Codification API

### POST /codify/batch

Run vehicle codification on transformed data.

**Parameters:**
- `run_id` (optional): Existing run ID to process
- `case_id` (optional): Case ID for new runs

**Response:**
```json
{
  "run_id": "uuid",
  "metrics": {
    "rows_total": 45,
    "auto_accept": 38,
    "needs_review": 5,
    "no_match": 2,
    "t_high": 0.90,
    "t_low": 0.70
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/codify/batch?run_id=transform-uuid"
```

---

## Export API

### POST /export

Export run data to Gcotiza Excel format.

**Parameters:**
- `run_id` (required): Run identifier to export
- `template` (optional): Template path (default: `configs/gcotiza-templates/gcotiza_v1.yaml`)

**Response:**
```json
{
  "url": "s3://exports/gcotiza/uuid_20240915_143022.xlsx",
  "checksum": "sha256-hash",
  "rows": 45,
  "columns": 46
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/export?run_id=codify-uuid"
```

### GET /export/download

Get presigned download URL for an exported file.

**Parameters:**
- `run_id` (required): Run identifier
- `expiration` (optional): URL expiration in seconds (default: 3600)

**Response:**
```json
{
  "download_url": "https://s3-presigned-url...",
  "expires_in": 3600,
  "checksum": "sha256-hash",
  "created_at": "2024-09-15T14:30:22.123456"
}
```

---

## Vehicle Codifier API

The Vehicle Codifier service provides advanced vehicle matching and AMIS/CVEGS codification capabilities.

### POST /match

Unified endpoint for vehicle matching - handles both single vehicles and batches.

**Single Vehicle Request:**
```json
{
  "description": "TOYOTA YARIS SOL L 2020",
  "brand": "TOYOTA",
  "model": "YARIS",
  "year": 2020,
  "insurer_id": "default"
}
```

**Batch Request:**
```json
{
  "vehicles": [
    {
      "description": "TOYOTA YARIS SOL L 2020",
      "brand": "TOYOTA",
      "model": "YARIS",
      "year": 2020
    }
  ],
  "insurer_id": "default",
  "parallel_processing": true
}
```

**Response:**
```json
{
  "results": [
    {
      "cvegs_code": "1234567890",
      "confidence_score": 0.92,
      "confidence_level": "high",
      "matched_brand": "TOYOTA",
      "matched_model": "YARIS",
      "matched_year": 2020,
      "processing_time_ms": 245.7,
      "candidates": [
        {
          "cvegs": "1234567890",
          "score": 0.92,
          "label": "toyota yaris 2020 hatchback particular"
        }
      ]
    }
  ]
}
```

### POST /codify/batch

Database-driven batch codification for background processing.

**Parameters:**
- `run_id` (optional): Existing run ID to process
- `case_id` (optional): Case ID for new runs

**Response:**
```json
{
  "run_id": "uuid",
  "metrics": {
    "rows_total": 150,
    "auto_accept": 135,
    "needs_review": 12,
    "no_match": 3,
    "t_high": 0.90,
    "t_low": 0.70
  }
}
```

### GET /datasets/stats

Get statistics about loaded AMIS datasets.

**Response:**
```json
{
  "default": {
    "records": 50000,
    "brands": 120,
    "models": 3500,
    "last_updated": "2024-09-15T10:30:00Z"
  }
}
```

### GET /metrics

Get comprehensive service metrics including Clean Architecture status.

**Response:**
```json
{
  "service_info": {
    "name": "Vehicle Codifier Service",
    "architecture": "Clean Architecture with Domain-Driven Design",
    "features": {
      "ai_powered_matching": true,
      "batch_processing": true,
      "excel_integration": true
    }
  },
  "performance_optimizations": {
    "repository_caching": true,
    "chunked_batch_processing": true,
    "controlled_concurrency": true
  }
}
```

---

## Smart Intake API

### POST /process-email

Process manual email data with attachments and broker profile detection.

**Content-Type**: `multipart/form-data`

**Form Fields:**
- `from_email` (required): Email sender address
- `subject` (required): Email subject line  
- `received_date` (optional): Date email was received
- `content` (required): Email body content
- `attachment_0`, `attachment_1`, ... (optional): File attachments

**Example Request:**
```bash
curl -X POST "http://localhost:8002/process-email" \
  -F "from_email=broker@luckygas.com.mx" \
  -F "subject=Fleet Insurance Request - Acme Corp" \
  -F "content=Please find attached our vehicle list for insurance quote..." \
  -F "attachment_0=@fleet_vehicles.xlsx"
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "case_id": "EMAIL_20240915_143022", 
  "status": "processing",
  "broker_profile": {
    "profile_id": "lucky_gas.yaml",
    "name": "Lucky Gas Fleet Profile",
    "confidence": 0.95
  },
  "message": "Email processing started successfully"
}
```

### GET /broker-profiles/detect

Detect broker profile from email address domain.

**Parameters:**
- `email` (required): Email address to analyze

**Example Request:**
```bash
curl "http://localhost:8002/broker-profiles/detect?email=broker@luckygas.com.mx"
```

**Response:**
```json
{
  "email_domain": "luckygas.com.mx",
  "profile_found": true,
  "profile_id": "lucky_gas.yaml",
  "name": "Lucky Gas Fleet Profile", 
  "confidence": 0.95,
  "field_mappings": {
    "marca": "brand",
    "submarca": "model",
    "año": "year",
    "descripción": "description"
  }
}
```

### GET /broker-profiles

Get all available broker profiles with usage statistics.

**Response:**
```json
{
  "profiles": [
    {
      "domain": "luckygas.com.mx",
      "profile_id": "lucky_gas.yaml",
      "name": "Lucky Gas Fleet Profile",
      "confidence": 0.95,
      "auto_generated": false,
      "usage_count": 47,
      "last_used": "2024-09-15T14:30:22Z"
    },
    {
      "domain": "axa.com.mx", 
      "profile_id": "axa_seguros.yaml",
      "name": "AXA Seguros Profile",
      "confidence": 0.89,
      "auto_generated": true,
      "usage_count": 12,
      "last_used": "2024-09-14T10:15:33Z"
    }
  ]
}
```

### POST /broker-profiles

Create a new broker profile (typically auto-generated).

**Request Body:**
```json
{
  "domain": "newbroker.com",
  "name": "Auto-generated Profile for New Broker",
  "profile_id": "newbroker_auto.yaml", 
  "confidence": 0.78,
  "field_mappings": {
    "Vehicle Make": "brand",
    "Vehicle Model": "model",
    "Model Year": "year",
    "Full Description": "description"
  },
  "auto_generated": true
}
```

**Response:**
```json
{
  "message": "Profile created",
  "domain": "newbroker.com",
  "profile_id": "newbroker_auto.yaml"
}
```

### GET /status/{run_id}

Get processing status for email intake runs.

**Response:**
```json
{
  "run_id": "uuid",
  "case_id": "EMAIL_20240915_143022",
  "status": "codifying",
  "progress": 65,
  "current_step": "Running AI vehicle matching",
  "broker_profile": "lucky_gas.yaml",
  "attachments_processed": 1,
  "vehicles_extracted": 15,
  "estimated_completion": "2024-09-15T14:35:00Z"
}
```

---

## Data Models

### Transform Input Format

The transform engine expects broker Excel/CSV files with columns that map to canonical fields:

**Lucky Gas Profile Mapping:**
- `marca` → `brand`
- `submarca` → `model`
- `año` → `year`
- `carrocería` → `body`
- `uso` → `use`

### Canonical Vehicle Format

After transformation, vehicles are normalized to:

```json
{
  "brand": "nissan",
  "model": "sentra", 
  "year": 2020,
  "body": "sedan",
  "use": "particular",
  "description": "nissan sentra 2020 sedan particular",
  "license_plate": "ABC-123",
  "insured_value": 250000.0,
  "premium": 12500.0
}
```

### Codification Result

Each vehicle gets a codification result:

```json
{
  "run_id": "uuid",
  "row_idx": 0,
  "suggested_cvegs": "123456",
  "confidence": 0.95,
  "decision": "auto_accept",
  "candidates": [
    {
      "cvegs": "123456",
      "score": 0.95,
      "label": "nissan sentra 2020 sedan particular"
    }
  ]
}
```

### Export Output

Gcotiza exports contain 46 columns (A-AT) including:

**Vehicle Identification:**
- `CLAVE VEHICULO` (CVEGS code)
- `MARCA`, `MODELO`, `AÑO`
- `CARROCERIA`, `USO`, `DESCRIPCION`

**Coverage Fields (P-AT):**
- `DED DM PP`, `DED RT`, `RC LIMITE`
- Insurance conditions, deductibles, limits
- Territory, validity, payment terms

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error description",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional context"
  }
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Resource not found
- `500`: Internal Server Error

---

## Examples

### Complete Workflow

```bash
# 1. Transform broker data
TRANSFORM_RESULT=$(curl -s -X POST "http://localhost:8000/transform?case_id=demo&s3_uri=s3://bucket/fleet.xlsx")
RUN_ID=$(echo $TRANSFORM_RESULT | jq -r '.run_id')

# 2. Preview results
curl "http://localhost:8000/transform/preview?run_id=$RUN_ID&limit=5"

# 3. Run codification
curl -X POST "http://localhost:8000/codify/batch?run_id=$RUN_ID"

# 4. Export to Gcotiza
EXPORT_RESULT=$(curl -s -X POST "http://localhost:8000/export?run_id=$RUN_ID")
echo $EXPORT_RESULT | jq '.url'

# 5. Get download link
curl "http://localhost:8000/export/download?run_id=$RUN_ID"
```

### Testing with Sample Data

```bash
# Load sample AMIS catalogue
./tools/load_amis.py --file data/samples/amis_sample.xlsx

# Build embeddings
./tools/build_embeddings.py --batch-size 32

# Test search functionality
./tools/search_amis.py search "Honda Civic 2020 sedan"

# Evaluate codifier accuracy
./tools/eval_codifier.py --file data/samples/labeled_100.csv
```