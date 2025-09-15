# Minca AI Insurance Processing Platform

A comprehensive, modular monorepo for AI-powered insurance data processing. Transform broker files into standardized Gcotiza format using ML-driven vehicle codification and configurable transformation rules.

## 🏗️ Architecture

```
MVP_underwriting/
├─ services/               # Microservices
│  ├─ api/                 # FastAPI: Main REST API, orchestration
│  ├─ document-processor/  # Unified Excel processing (extract, transform, export)
│  ├─ vehicle-codifier/    # Unified AMIS/CVEGS vehicle matching (web API + worker)
│  ├─ smart-intake-service/ # Outlook email processing and intake
│  └─ worker-transform/    # Background transformation workers
├─ packages/               # Shared Libraries
│  ├─ db/                  # SQLAlchemy models + Alembic migrations
│  ├─ ml/                  # Text normalization + embeddings + retrieval
│  ├─ profiles/            # Transform engine DSL + runner
│  ├─ schemas/             # Pydantic data validation schemas
│  └─ storage/             # S3/MinIO utilities
├─ configs/                # Business Logic Configuration
│  ├─ broker-profiles/     # YAML transformation rules per broker
│  ├─ gcotiza-templates/   # Export format specifications
│  └─ aliases/             # Vehicle normalization dictionaries
├─ tools/                  # CLI Utilities
│  ├─ load_amis.py         # AMIS catalogue data loader
│  ├─ build_embeddings.py  # ML embedding index builder
│  ├─ search_amis.py       # Semantic vehicle search
│  └─ eval_codifier.py     # Accuracy evaluation framework
├─ data/                   # Sample Data
├─ reports/                # Evaluation Reports
├─ ui/                     # Next.js React Frontend
└─ infra/                  # Infrastructure (Future)
```

## 🚀 How to Run the Project

### Prerequisites

- **Docker & Docker Compose**: For containerized services
- **Poetry**: Python dependency manager (`curl -sSL https://install.python-poetry.org | python3 -`)
- **Python 3.11+**: For CLI tools

### Step 1: Environment Setup

```bash
# Create environment file from template
cp configs/env/.env.example configs/env/.env.development

# Edit configs/env/.env.development if needed (default values work for development)
# Most settings work out of the box for local development
# Only customize OPENAI_API_KEY if you need vehicle codification features

# For detailed environment configuration, see:
# docs/ENVIRONMENT_SETUP.md
```

## Run services with Docker Compose (per-service quick commands)
You can run each service individually with Docker Compose instead of using make.

Infra only (PostgreSQL + MinIO + bucket init)
```bash
# Start core infra
docker compose up -d db minio mc

# Tail logs
docker compose logs -f db minio mc
```

API service (FastAPI at http://localhost:8000)
```bash
docker compose build api
docker compose up -d api
curl -s http://localhost:8000/health
```

Document Processor (http://localhost:8001)
```bash
docker compose build document-processor
docker compose up -d document-processor
curl -s http://localhost:8001/health
```

Vehicle Codifier (http://localhost:8002)
```bash
# Build and run service
docker compose build vehicle-codifier
docker compose up -d vehicle-codifier
curl -s http://localhost:8002/health
```
Notes:
- By default the service looks for an Excel dataset at data/cvegs_dataset.xlsx inside the container. If you have a dataset on your host, mount it and/or set CVEGS_DATASET_PATH. Example:
  ```yaml
  # In docker-compose.yml (vehicle-codifier service)
  environment:
    - CVEGS_DATASET_PATH=/app/services/vehicle-codifier/data/cvegs_dataset.xlsx
  volumes:
    - ./data/cvegs_dataset.xlsx:/app/services/vehicle-codifier/data/cvegs_dataset.xlsx:ro
  ```
- The service starts even without a dataset (health/docs available). Initialize later after mounting a dataset: POST /insurers/default/initialize.

Frontend UI (Next.js at http://localhost:3000)
```bash
docker compose build ui
docker compose up -d ui
```

Common compose operations
```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# Stop and remove containers (keep volumes)
docker compose down

# Stop and remove containers + named volumes
docker compose down -v

# Tail logs (any service)
docker compose logs -f api
docker compose logs -f document-processor
docker compose logs -f vehicle-codifier
docker compose logs -f ui
```

### Step 2: Start Services

```bash
# Start all services (PostgreSQL + pgvector, MinIO, API)
make dev

# This will:
# - Build and start all services (Database, Storage, APIs, Frontend)
# - PostgreSQL with pgvector extension on port 5432
# - MinIO S3-compatible storage on ports 9000/9001  
# - Main API service on port 8000
# - Document processor service on port 8001
# - Vehicle codifier service on port 8002
# - Next.js frontend on port 3000

# Monitor logs (optional)
make logs

# Stop services when done
make stop
```

### Step 3: Initialize Database

```bash
# Run database migrations
cd packages/db
poetry run alembic upgrade head
cd ../..
```

### Step 4: Load Sample Data & Build Embeddings

```bash
# Load AMIS vehicle catalogue (sample data)
./tools/load_amis.py --file data/amis_sample.xlsx

# Build ML embeddings for semantic search
./tools/build_embeddings.py --batch-size 32
```

### Step 5: Test the System

```bash
# Health check
curl http://localhost:8000/health

# Test codifier with sample data
./tools/eval_codifier.py --file data/samples/labeled_100.csv

# Search for vehicles
./tools/search_amis.py "Toyota Corolla 2020"
```

### Development URLs

- **Frontend**: http://localhost:3000 (Next.js React app)
- **Main API**: http://localhost:8000 (FastAPI docs at `/docs`)
- **Document Processor**: http://localhost:8001 (Excel processing service at `/docs`)
- **Vehicle Codifier**: http://localhost:8002 (AMIS/CVEGS matching service at `/docs`)
- **MinIO Console**: http://localhost:9001 (minio/minio12345)
- **PostgreSQL**: localhost:5432 (minca/minca)

### API Endpoints

#### Main API (Port 8000)
```bash
# Health check
GET /health

# Vehicle codification
POST /codify/batch?run_id=uuid&case_id=123

# Legacy transform endpoint
POST /transform?case_id=123&s3_uri=s3://bucket/file.xlsx&profile=lucky_gas.yaml
```

#### Document Processor API (Port 8001)
```bash
# Complete processing pipeline
POST /process
  - file: Excel/CSV file
  - case_id: Case identifier
  - profile: Broker profile (default: generic.yaml)
  - export_template: Export template (default: gcotiza_v1.yaml)

# Individual processing steps
POST /extract          # Extract data from uploaded file
POST /transform/{run_id}?profile=generic.yaml
POST /export/{run_id}?template=gcotiza_v1.yaml

# Status monitoring
GET /status/{run_id}    # Real-time processing status

# Health check
GET /health
```

#### Vehicle Codifier API (Port 8002)
```bash
# Vehicle matching (single or batch)
POST /match

# Batch codification (worker-style)
POST /codify/batch?run_id=uuid&case_id=123

# Health check
GET /health

# Service metrics
GET /metrics
```

## 📊 Processing Workflow

### Claveteador End-to-End Workflow

The platform now features a complete **Claveteador workflow** that provides an intuitive, step-by-step process for insurance case processing:

```
Smart Intake → Claveteador → Vehicle Matching → Excel Export
     ↓              ↓              ↓              ↓
Email Processing  Data Review   AMIS Matching   Final Export
Attachment Parse  Form Validation  Code Assignment  Excel Generation
Broker Detection  Coverage Setup   Manual Editing   Agent Discount
```

#### **Step 1: Smart Intake Dashboard**
- **Email Results Display**: Shows processed smart intake cases with status indicators
- **Pre-Analysis Status**: Visual badges for "Completo" vs "Incompleto" cases
- **Action Buttons**: "Process" for complete cases, "Ask Info" for incomplete ones
- **Filtering & Search**: Filter by status, date, and other criteria

#### **Step 2: Claveteador (Data Preprocessing)**
- **Email Content Review**: Display original email with subject, sender, content
- **Company Information Form**: Editable form with required fields (Nombre, RFC, Domicilio, etc.)
- **Coverage Configuration**: Interactive tables for Auto, Remolques, Camiones Pesado, Moto coverage
- **Attachments Management**: Excel file display with vehicle count detection
- **Claims History**: PDF reports with download functionality
- **Missing Field Highlighting**: Yellow highlights and red labels for incomplete data

#### **Step 3: Vehicle Matching (AMIS Codification)**
- **Codification Summary**: Statistics showing Total Vehicles, AMIS Found, Uncertain, Failed
- **Interactive Vehicle Table**: Editable table with inline editing for corrections
- **Status Indicators**: Visual status for Complete, Missing VIN/Suma, Uncertain, Failed
- **AMIS Code Validation**: OK/FAIL status with manual override capability
- **Filtering & Pagination**: Filter by AMIS status, paginated results

#### **Step 4: Excel Export**
- **Final Data Review**: Complete Mexican insurance columns (Marca, Serie, Año, etc.)
- **Agent Discount Control**: Editable discount percentage (default 15%)
- **Professional Export**: Generate Excel Cotizador with proper formatting
- **Workflow Completion**: All steps marked as completed

### Traditional Processing Pipeline

1. **📁 Extract**: Parse Excel/CSV files with intelligent header mapping
2. **🔄 Transform**: Apply broker profile rules (normalize, validate, compute fields)
3. **🤖 Codify**: ML embeddings + fuzzy matching → AMIS CVEGS codes + confidence
4. **👀 Review**: Manual review of low-confidence matches via Claveteador workflow
5. **📤 Export**: Generate Gcotiza-ready Excel with professional formatting + S3 upload

### Document Processing Pipeline

The **Document Processor Service** handles the complete document lifecycle:

```
Excel/CSV → Extract → Transform → Codify → Export → Download
    ↓         ↓         ↓         ↓        ↓         ↓
   Parse   Validate   Apply    Add AI   Format   S3 URL
  Headers   Data    Profiles  Codes    Excel
```

### Current Implementation Status

✅ **Document Processing Service** (Consolidated)
- **Excel Extraction**: Intelligent header mapping with 80+ synonyms (Spanish/English)
- **Data Validation**: Comprehensive VIN, year, and business rule validation
- **Profile Transformation**: YAML-based broker profiles with field mapping
- **Professional Export**: Gcotiza-ready Excel with 46 columns and formatting
- **Async Processing**: Background task processing with real-time status tracking

✅ **AMIS Catalogue System**
- Vehicle database loading with aliases
- Multilingual text normalization  
- Semantic embeddings with pgvector
- Top-K similarity search with fallback strategies

✅ **Vehicle Codification**
- Hybrid scoring: 70% embeddings + 30% fuzzy matching
- Three-tier decisions: auto_accept (90%+), needs_review (70-90%), no_match (<70%)
- Comprehensive evaluation framework

✅ **Frontend Interface**
- React + Next.js dashboard with real-time processing status
- Drag & drop file upload with broker profile selection
- Vehicle search with semantic matching
- Export download and results visualization

## 🛠️ Technology Stack

**Frontend**: Next.js 15, React 18, TypeScript, Tailwind CSS  
**Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic  
**Dependency Management**: Poetry workspace mode, npm  
**Database**: PostgreSQL + pgvector extension  
**Storage**: MinIO (dev) / S3 (prod)  
**ML**: sentence-transformers, rapidfuzz, pandas, numpy  
**Excel Processing**: openpyxl with professional formatting  
**Infrastructure**: Docker Compose (dev) / AWS ECS (future)  
**Text Processing**: Unicode normalization + abbreviation expansion

## 🔧 Troubleshooting

### Common Issues

**Docker build fails with "does not contain any element"**
```bash
# Fixed in both API and Document Processor services
# Poetry now uses --no-root flag to avoid installing projects before copying source
# Both services/api/Dockerfile and services/document-processor/Dockerfile updated
```

**Permission denied on CLI tools**
```bash
# Make CLI tools executable
chmod +x tools/*.py
```

**Database connection issues**
```bash
# Check if PostgreSQL is running
docker ps | grep minca_db

# Reset database if needed
make stop
docker volume rm mvp_underwriting_db_data
make dev
```

**Poetry not found**
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
# Add to PATH (follow installation instructions)
```

**MinIO buckets not created**
```bash
# Check MinIO setup container logs
docker logs minca_minio_mc

# Manually create buckets if needed
docker exec -it minca_minio mc alias set local http://localhost:9000 minio minio12345
docker exec -it minca_minio mc mb local/raw local/exports
```

### Development Commands

```bash
# Format code
make fmt

# Run linting
make lint

# View service logs
make logs

# Stop all services and remove volumes
make stop
```

## 📚 Documentation

- **[API Reference](docs/api.md)**: Complete REST API documentation
- **[Development Guide](docs/development.md)**: Detailed development setup and workflows

---

**Minca AI** - Transforming insurance data processing with AI 🚀
