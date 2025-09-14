# Development Guide

## Setup

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- Docker & Docker Compose
- Git

### Installation

1. **Install Poetry**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd MVP_underwriting
   
   # Install workspace dependencies
   poetry install
   ```

3. **Start Development Environment**
   ```bash
   # Start PostgreSQL + MinIO + pgAdmin
   make dev
   ```

4. **Initialize Database**
   ```bash
   cd packages/db
   poetry run alembic upgrade head
   ```

5. **Load Sample Data**
   ```bash
   # Load AMIS vehicle catalogue
   ./tools/load_amis.py --file data/samples/amis_sample.xlsx
   
   # Build ML embeddings
   ./tools/build_embeddings.py --batch-size 32
   ```

## Project Structure

```
MVP_underwriting/
├─ services/               # Microservices
│  ├─ api/                 # FastAPI REST API
│  ├─ worker-codifier/     # Vehicle codification
│  ├─ worker-transform/    # Data transformation  
│  └─ worker-exporter/     # Excel export generation
├─ packages/               # Shared libraries
│  ├─ db/                  # Database models & migrations
│  ├─ ml/                  # ML utilities & embeddings
│  ├─ profiles/            # Transform engine DSL
│  ├─ schemas/             # Pydantic schemas
│  └─ storage/             # S3 utilities
├─ configs/                # Business configuration
│  ├─ broker-profiles/     # Transformation rules
│  ├─ gcotiza-templates/   # Export templates
│  └─ aliases/             # Normalization dictionaries
└─ tools/                  # CLI utilities
```

## Development Workflow

### 1. Package Development

Each package is independently versioned with Poetry:

```bash
# Work on a specific package
cd packages/ml
poetry install
poetry shell

# Run tests
poetry run pytest

# Add dependencies
poetry add sentence-transformers
```

### 2. Service Development

Services depend on packages via workspace and automatically load environment configuration:

```bash
# Start API service
cd services/api
poetry install
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# The service will automatically load:
# - configs/env/.env.development (base environment)
# - configs/env/service-specific/.env.api (service-specific config)

# Check service dependencies
poetry show --tree

# Verify environment loading
curl http://localhost:8000/health
```

**Environment Loading Notes:**
- Services use dynamic path resolution to find environment files
- Startup logs show which environment files are loaded
- No manual environment setup needed - everything is automatic
- Works from any service directory within the project

### 3. Database Changes

```bash
cd packages/db

# Create migration
poetry run alembic revision --autogenerate -m "Add new table"

# Apply migration
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

### 4. Configuration Updates

- **Broker Profiles**: Edit `configs/broker-profiles/`
- **Export Templates**: Edit `configs/gcotiza-templates/`
- **Aliases**: Edit `configs/aliases/`

## Testing

### Unit Tests

```bash
# Run all tests
poetry run pytest

# Run specific package tests
cd packages/ml
poetry run pytest tests/

# With coverage
poetry run pytest --cov=app
```

### Integration Tests

```bash
# Test complete pipeline
./tools/test_pipeline.py --case-id test-case

# Test individual components
curl -X POST "http://localhost:8000/transform?case_id=test"
curl -X POST "http://localhost:8000/codify/batch?run_id=uuid"
curl -X POST "http://localhost:8000/export?run_id=uuid"
```

### Performance Testing

```bash
# Evaluate codifier accuracy
./tools/eval_codifier.py --file data/samples/labeled_100.csv

# Benchmark embedding generation
./tools/build_embeddings.py --batch-size 64 --limit 1000

# Test search performance
./tools/search_amis.py search "Honda Civic 2020" --k 50
```

## Common Tasks

### Adding a New Broker Profile

1. **Create Profile YAML**
   ```yaml
   # configs/broker-profiles/new_broker.yaml
   detect:
     required_headers: ["vehicle_make", "vehicle_model", "model_year"]
   mapping:
     columns:
       "vehicle_make": brand
       "vehicle_model": model
       "model_year": year
     normalize:
       brand: "lower, strip, deburr"
   validate:
     required: ["brand", "model", "year"]
   ```

2. **Test Profile**
   ```bash
   # Transform with new profile
   curl -X POST "http://localhost:8000/transform?profile=new_broker.yaml&..."
   ```

### Adding New Aliases

1. **Update Alias Files**
   ```yaml
   # configs/aliases/brands.yaml
   toyota:
     - toyoya
     - toyota motor
   ```

2. **Rebuild Embeddings** (if needed)
   ```bash
   ./tools/build_embeddings.py --force-rebuild
   ```

### Adding Export Fields

1. **Update Template**
   ```yaml
   # configs/gcotiza-templates/gcotiza_v2.yaml
   columns:
     - name: "NEW_FIELD"
       key: "new_field"
       type: "text"
   ```

2. **Test Export**
   ```bash
   curl -X POST "http://localhost:8000/export?template=gcotiza_v2.yaml&..."
   ```

## Debugging

### Database Inspection

```bash
# Connect to PostgreSQL
docker exec -it mvp_db psql -U minca -d minca

# View tables
\dt

# Query runs
SELECT * FROM runs ORDER BY created_at DESC LIMIT 10;

# Check embeddings
SELECT COUNT(*) FROM amiscatalog WHERE embedding IS NOT NULL;
```

### Log Analysis

```bash
# API logs
docker logs mvp_api

# Service logs in development
poetry run uvicorn app.main:app --log-level debug
```

### ML Debugging

```bash
# Test embeddings directly
python -c "
from packages.ml.src.app.ml.embed import get_embedder
embedder = get_embedder()
result = embedder.embed_vehicle('Honda', 'Civic', 2020)
print(f'Embedding shape: {result.shape}')
"

# Test search
./tools/search_amis.py search "Honda Civic" --output-mode content -n
```

## Performance Guidelines

### Database

- Use indexes on frequently queried columns
- Batch database operations when possible
- Monitor query performance with `EXPLAIN ANALYZE`

### ML Operations

- Use appropriate batch sizes (16-64 for embeddings)
- Cache embedder instance to avoid model reloading
- Monitor GPU/CPU usage during ML operations

### File Processing

- Stream large files instead of loading into memory
- Use appropriate chunk sizes for S3 uploads
- Implement proper cleanup of temporary files

## Code Style

### Python

```bash
# Format code
poetry run black .
poetry run ruff check --fix .

# Type checking
poetry run mypy .
```

### Configuration

- Use consistent naming in YAML files
- Add comments for complex transformations
- Validate YAML syntax before committing

## Deployment

### Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Check service health
curl http://localhost:8000/health
```

### Production (Future)

- Use environment-specific configurations
- Implement proper secret management
- Set up monitoring and alerting
- Use production-grade databases

## Troubleshooting

### Common Issues

1. **"Role minca does not exist"**
   ```bash
   make dev  # Restart development environment
   ```

2. **"Module not found" errors**
   ```bash
   poetry install  # Reinstall dependencies
   ```

3. **"Embedding dimension mismatch"**
   ```bash
   ./tools/build_embeddings.py --force-rebuild
   ```

4. **"S3 connection failed"**
   - Check MinIO is running: `docker ps`
   - Verify environment variables

5. **Environment variables not loading when running services directly**
   ```bash
   # Check startup logs for environment loading messages:
   # ✅ Loaded .env.development
   # ✅ Loaded .env.api
   
   # If you see path errors, verify you're in the correct directory:
   pwd  # Should be in services/{service-name}
   
   # Check if environment files exist:
   ls -la ../../configs/env/.env.development
   ls -la ../../configs/env/service-specific/.env.api
   ```

6. **Service fails to start with path resolution errors**
   ```bash
   # Ensure you're running from the service directory:
   cd services/api  # or other service
   poetry run uvicorn src.api.main:app --reload
   
   # The service uses dynamic path resolution to find project root
   # and automatically loads the correct environment files
   ```

### Getting Help

- Check API documentation: `docs/api.md`
- Review configuration examples in `configs/`
- Test with sample data in `data/samples/`
