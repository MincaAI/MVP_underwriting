# Vehicle Catalog Management Workflow

This document describes the S3-only vehicle catalog management system with CATVER schema, structured labels, embeddings, and activation workflow.

## Overview

The system uses **S3 + Postgres** for vehicle catalog management with no local file dependencies. All catalog data flows through immutable S3 storage to versioned Postgres tables with structured labels and ML embeddings.

### Key Features
- **CATVER Schema**: Full support for Mexican insurance CATVER format (14 columns)
- **Structured Labels**: Fixed-order text representation for consistent embeddings
- **S3-Only Storage**: No local dataset dependencies
- **Version Control**: Multiple catalog versions with atomic activation

## Workflow Steps

### 1. Upload Catalog to S3 (Immutable Storage)

```bash
# Upload Excel file to S3 with versioning
aws s3 cp catalog.xlsx s3://raw/catalogs/v1.0.0/amis_catalog.xlsx

# Or use web interface/API to upload with automatic versioning
```

### 2. ETL: S3 → Postgres (Download to Temp)

```bash
# Load from S3 URI (recommended)
python tools/catalog_load.py \
  --version "v1.0.0" \
  --s3-uri "s3://raw/catalogs/v1.0.0/amis_catalog.xlsx" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca"

# Alternative: Load from local file (development only)
python tools/catalog_load.py \
  --version "v1.0.0" \
  --file "data/amis_sample.xlsx" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca"
```

**What happens:**
- Downloads CATVER Excel from S3 to temporary file
- Validates all required CATVER columns exist
- Maps Excel columns to database schema (1:1 mapping)
- Generates structured labels with fixed order
- Loads data into `amis_catalog` table with full CATVER schema
- Updates `catalog_import` table with status: `UPLOADED` → `LOADED`
- Cleans up temporary file

**CATVER Excel Columns Required:**
`MARCA`, `SUBMARCA`, `NUMVER`, `RAMO`, `CVEMARC`, `CVESUBM`, `MARTIP`, `CVESEGM`, `MODELO`, `CVEGS`, `DESCVEH`, `IDPERDIOD`, `SUMABAS`, `TIPVEH`

### 3. Generate Embeddings (384-dimensional)

```bash
# Generate embeddings for the catalog version
python tools/catalog_embed.py \
  --version "v1.0.0" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --model-id "intfloat/multilingual-e5-small"
```

**What happens:**
- Reads structured labels from `amis_catalog.label` column
- Auto-detects available libraries (sentence-transformers vs fallback)
- Generates 384-dimensional embeddings using multilingual model
- Stores embeddings in `amis_catalog.embedding` column (pgvector)
- Creates HNSW index for fast similarity search
- Updates `catalog_import` status: `LOADED` → `EMBEDDED`

**Structured Label Format:**
```
modelo=<year> | marca=<brand> | submarca=<model> | numver=<numver> | ramo=<ramo> | cvemarc=<cvemarc> | cvesubm=<cvesubm> | martip=<martip> | cvesegm=<segment> | descveh=<description> | idperdiod=<period> | sumabas=<sum> | tipveh=<vehicle_type>
```

**Example Label:**
```
modelo=2020 | marca=renault | submarca=zoe | numver=2002 | ramo=711 | cvemarc=37 | cvesubm=1344 | martip=615 | cvesegm=compacto | descveh=zoe bose 92 cp 5 puertas electrico | idperdiod=202002 | sumabas=382003.0 | tipveh=auto
```

### 4. Activate Version

```bash
# Activate the catalog version (only one can be active)
python tools/catalog_activate.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  activate --version "v1.0.0"
```

**What happens:**
- Deactivates all other versions
- Sets specified version as `ACTIVE` in `catalog_import`
- Only one version can be active at a time

## Management Commands

### List All Versions

```bash
python tools/catalog_activate.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  list
```

Example output:
```
Version              Status       Rows     Model                Created
v1.0.0              [ACTIVE]     15000    sentence-transformers... 2024-01-15 10:30
v0.9.0              EMBEDDED     14500    sentence-transformers... 2024-01-10 09:15
```

### Rebuild Embeddings

```bash
# Force rebuild embeddings for a version
python tools/build_embeddings.py \
  --version "v1.0.0" \
  --force-rebuild
```

## Database Schema

### catalog_import Table
Tracks catalog versions and their processing status:

```sql
CREATE TABLE catalog_import (
    version TEXT PRIMARY KEY,
    s3_uri TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    rows_loaded INTEGER,
    model_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('UPLOADED','LOADED','EMBEDDED','ACTIVE','FAILED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### amis_catalog Table
Stores the actual CATVER catalog data with structured labels and embeddings:

```sql
CREATE TABLE amis_catalog (
    id BIGSERIAL PRIMARY KEY,
    catalog_version TEXT NOT NULL,

    -- CATVER-specific columns (matching Excel structure)
    marca VARCHAR(25) NOT NULL,           -- Brand
    submarca VARCHAR(52) NOT NULL,        -- Sub-brand/Model
    numver INTEGER NOT NULL,              -- Version number
    ramo INTEGER NOT NULL,                -- Insurance branch
    cvemarc INTEGER NOT NULL,             -- Brand code
    cvesubm INTEGER NOT NULL,             -- Sub-brand code
    martip INTEGER NOT NULL,              -- Brand type
    cvesegm VARCHAR(51) NOT NULL,         -- Segment code
    modelo INTEGER NOT NULL,              -- Year
    cvegs INTEGER NOT NULL,               -- Unique vehicle code
    descveh VARCHAR(150) NOT NULL,        -- Vehicle description
    idperdiod INTEGER NOT NULL,           -- Period ID
    sumabas FLOAT NOT NULL,               -- Base sum
    tipveh VARCHAR(19) NOT NULL,          -- Vehicle type

    -- Structured text representation
    label TEXT,                           -- Fixed-order label for embeddings

    -- ML and metadata columns
    embedding VECTOR(384),                -- 384-dimensional embedding
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Status Flow

```
UPLOADED → LOADED → EMBEDDED → ACTIVE
    ↓         ↓         ↓         ↓
 S3 stored  In DB   +Embeddings  Live
```

## Configuration

### Environment Variables

No local dataset paths needed. Uses standard S3 + DB configuration:

```bash
# Database
DATABASE_URL=postgresql+psycopg://minca:minca@localhost:5432/minca

# S3 Storage
S3_ENDPOINT_URL=http://localhost:9000  # MinIO for dev
AWS_ACCESS_KEY_ID=minio
AWS_SECRET_ACCESS_KEY=minio12345
S3_BUCKET_RAW=raw

# ML Configuration
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
SIMILARITY_THRESHOLD=0.70
FUZZY_MATCH_THRESHOLD=0.80
W_EMBED=0.7
W_FUZZY=0.3
```

## Benefits

### ✅ Advantages
- **CATVER Compliance**: Full support for Mexican insurance CATVER format
- **Structured Labels**: Fixed-order text representation for consistent embeddings
- **Immutable Storage**: S3 provides tamper-proof catalog storage
- **Version Control**: Multiple catalog versions can coexist
- **No Local Dependencies**: No need for local dataset files
- **Atomic Activation**: Clean switchover between catalog versions
- **Integrity Checking**: SHA256 hashes ensure data integrity
- **Scalable**: Works with catalogs of any size
- **Cloud-Ready**: Full S3 compatibility for production

### ✅ Workflow Guarantees
- Only one catalog version can be active at a time
- All embeddings use consistent 384-dimensional vectors
- Failed operations don't affect existing active catalogs
- Complete audit trail of all catalog changes

## Example: Complete Workflow

```bash
# 1. Upload new catalog version
aws s3 cp new_catalog.xlsx s3://raw/catalogs/v2.0.0/

# 2. Load from S3
python tools/catalog_load.py \
  --version "v2.0.0" \
  --s3-uri "s3://raw/catalogs/v2.0.0/new_catalog.xlsx" \
  --db $DATABASE_URL

# 3. Generate embeddings
python tools/catalog_embed.py \
  --version "v2.0.0" \
  --db $DATABASE_URL \
  --model-id "intfloat/multilingual-e5-small"

# 4. Activate new version
python tools/catalog_activate.py \
  --db $DATABASE_URL \
  activate --version "v2.0.0"

# 5. Verify activation
python tools/catalog_activate.py --db $DATABASE_URL list
```

This workflow ensures reliable, versioned catalog management with no local file dependencies.