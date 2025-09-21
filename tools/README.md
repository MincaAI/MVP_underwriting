# CLI Tools Documentation

This directory contains command-line utilities for managing the Minca AI Insurance Processing Platform. These tools provide administrative functions for catalog management, data processing, and system evaluation.

## Overview

| Tool | Purpose | Category |
|------|---------|----------|
| `catalog_load.py` | Load AMIS catalog data from S3/local files | Data Management |
| `catalog_embed.py` | Generate ML embeddings for catalog versions | Data Management |
| `catalog_activate.py` | Manage active catalog versions | Data Management |
| `delete_amis_data.py` | Safely delete AMIS catalog data | Data Management |
| `search_amis.py` | Semantic vehicle search and testing | Search & Testing |
| `eval_codifier.py` | Evaluate vehicle codifier accuracy | Evaluation |
| `build_embeddings.py` | Legacy embedding builder (deprecated) | Legacy |

## Data Management Tools

### catalog_load.py

Load AMIS catalog data with version management and S3 integration.

**Features:**
- S3 and local file support
- CATVER schema compliance (14 columns)
- Automatic text enhancement and normalization
- SHA256 integrity checking
- Structured label generation

**Usage:**
```bash
# Load from S3 (recommended)
python tools/catalog_load.py \
  --version "v2.0.0" \
  --s3-uri "s3://raw/catalogs/CATVER_ENVIOS.xlsx" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca"

# Load from local file
python tools/catalog_load.py \
  --version "v2.0.0" \
  --file "data/amis-catalogue/CATVER_ENVIOS.xlsx" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca"
```

**Parameters:**
- `--version` (required): Catalog version identifier
- `--s3-uri`: S3 URI to download catalog from
- `--file`: Local Excel file path (alternative to S3)
- `--db` (required): PostgreSQL database URL

### catalog_embed.py

Generate ML embeddings for loaded catalog versions using state-of-the-art models.

**Features:**
- sentence-transformers with intfloat/multilingual-e5-large
- 1024-dimensional embeddings with normalization
- Batch processing for large datasets
- Automatic index creation (HNSW)
- Progress tracking

**Usage:**
```bash
python tools/catalog_embed.py \
  --version "v2.0.0" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --model-id "intfloat/multilingual-e5-large" \
  --batch-size 2000
```

**Parameters:**
- `--version` (required): Catalog version to embed
- `--db` (required): Database URL
- `--model-id` (required): Model identifier for tracking
- `--batch-size`: Batch size for database insertion (default: 2000)

### catalog_activate.py

Manage which catalog version is active for vehicle matching services.

**Features:**
- List all available versions
- Activate specific versions
- Version status tracking
- Integration with matching services

**Usage:**
```bash
# List all versions
python tools/catalog_activate.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  list

# Activate specific version
python tools/catalog_activate.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  activate --version "v2.0.0"
```

### delete_amis_data.py

Safely delete AMIS catalog data with comprehensive safety features.

**Features:**
- Multiple deletion modes (all data, specific versions)
- Interactive confirmations with explicit phrases
- Row count preview before deletion
- Force mode for automation
- Version validation

**Usage:**
```bash
# Check current status
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action show-info

# List available versions
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action list-versions

# Delete specific version (safe)
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action delete-version \
  --version "v1.0.0"

# Delete all data (safe)
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action delete-all

# Force deletion (automation)
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action delete-all \
  --force
```

**Parameters:**
- `--db` (required): Database URL
- `--action` (required): `show-info`, `list-versions`, `delete-version`, `delete-all`
- `--version`: Catalog version (required for `delete-version`)
- `--force`: Skip confirmation prompts

**Safety Features:**
- **Row Count Display**: Shows exactly how many rows will be deleted
- **Explicit Confirmation**: Requires typing specific phrases like "DELETE v1.0.0"
- **Version Validation**: Checks if version exists before deletion
- **Clear Error Messages**: Detailed feedback for invalid operations

## Search & Testing Tools

### search_amis.py

Perform semantic vehicle searches against the active catalog.

**Features:**
- Embedding-based semantic search
- Fuzzy string matching fallback
- Confidence scoring
- Multiple result candidates

**Usage:**
```bash
# Search for vehicles
python tools/search_amis.py "Toyota Corolla 2020"
python tools/search_amis.py "Honda Civic Sedan"
```

## Evaluation Tools

### eval_codifier.py

Evaluate vehicle codifier accuracy using labeled test datasets.

**Features:**
- Precision/recall metrics
- Confidence threshold analysis
- Performance benchmarking
- Detailed error analysis

**Usage:**
```bash
# Evaluate with test dataset
python tools/eval_codifier.py --file data/samples/labeled_100.csv

# Custom evaluation parameters
python tools/eval_codifier.py \
  --file data/samples/labeled_100.csv \
  --threshold 0.85 \
  --max-candidates 10
```

## Complete Workflows

### Initial Setup Workflow

Set up a new AMIS catalog from scratch:

```bash
# 1. Load catalog data
python tools/catalog_load.py \
  --version "v1.0.0" \
  --s3-uri "s3://raw/catalogs/CATVER_ENVIOS.xlsx" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca"

# 2. Generate embeddings
python tools/catalog_embed.py \
  --version "v1.0.0" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --model-id "intfloat/multilingual-e5-large"

# 3. Activate the version
python tools/catalog_activate.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  activate --version "v1.0.0"

# 4. Test the setup
python tools/search_amis.py "Honda Civic 2020"
```

### Catalog Update Workflow

Update to a new catalog version:

```bash
# 1. Check current status
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action show-info

# 2. Load new version
python tools/catalog_load.py \
  --version "v2.0.0" \
  --s3-uri "s3://raw/catalogs/CATVER_ENVIOS_2024.xlsx" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca"

# 3. Generate embeddings
python tools/catalog_embed.py \
  --version "v2.0.0" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --model-id "intfloat/multilingual-e5-large"

# 4. Activate new version
python tools/catalog_activate.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  activate --version "v2.0.0"

# 5. Clean old version (optional)
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action delete-version \
  --version "v1.0.0"

# 6. Verify new setup
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action show-info
```

### Data Cleanup Workflow

Clean up catalog data for maintenance:

```bash
# 1. List all versions
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action list-versions

# 2. Delete specific old versions
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action delete-version \
  --version "v0.9.0"

# 3. Complete cleanup (if needed)
python tools/delete_amis_data.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --action delete-all
```

## Environment Setup

All tools require:

1. **Database Access**: PostgreSQL with pgvector extension
2. **Python Dependencies**: Install via Poetry in each service
3. **Environment Variables**: Database URLs and credentials
4. **S3 Access**: For S3-based catalog operations (MinIO or AWS S3)

**Database URL Format:**
```
postgresql+psycopg://user:password@host:port/database
```

**Example for Development:**
```
postgresql+psycopg://minca:minca@localhost:5432/minca
```

## Error Handling

All tools provide:
- Clear error messages with context
- Exit codes for automation (0 = success, 1 = error)
- Progress indicators for long-running operations
- Validation of inputs before execution

## Security Considerations

- **Database URLs**: Never commit database credentials to version control
- **S3 Access**: Use IAM roles in production, not access keys in environment
- **Force Mode**: Use `--force` flag carefully in automation scripts
- **Data Deletion**: Always verify deletions in staging before production

## Performance Notes

- **Batch Sizes**: Adjust `--batch-size` for embedding operations based on memory
- **Concurrent Operations**: Only run one embedding operation per database at a time
- **Large Catalogs**: For catalogs >100k records, consider chunked processing
- **Index Creation**: HNSW index creation may take several minutes for large datasets

## Legacy Tools

### build_embeddings.py (Deprecated)

**Status**: Replaced by `catalog_embed.py`
**Migration**: Use `catalog_embed.py` for all new embedding operations

The new tool provides better performance, safety features, and integration with the catalog versioning system.