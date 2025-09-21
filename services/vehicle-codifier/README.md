# Vehicle Codifier Service

A **simplified** vehicle codification service that provides accurate CVEGS matching using pgvector similarity search and CATVER structured labels. This service replaces the previous over-engineered Clean Architecture implementation.

## 🏗️ Architecture

Built using **simple, direct approach** with 5 core files:

```
vehicle-codifier/
├── src/vehicle_codifier/
│   ├── main.py         # FastAPI app (150 lines)
│   ├── service.py      # Core matching logic (200 lines)
│   ├── models.py       # Pydantic models (70 lines)
│   ├── config.py       # Settings (40 lines)
│   ├── utils.py        # LLM extraction (120 lines)
│   └── __init__.py     # Package init
├── test_service.py     # Test script
├── run_service.py      # Run script
├── Dockerfile
├── pyproject.toml
└── README.md

TOTAL: ~580 lines (vs 2000+ lines previously)
```

## ✨ Key Features

### 🎯 Processing Modes
- **Direct API**: Real-time vehicle matching (`/match`, `/match/batch`)
- **Database Integration**: Compatible with main API pipeline (`/codify/batch`)

### 🤖 Intelligent Matching
- **LLM Extraction**: OpenAI GPT extracts CATVER fields from descriptions
- **pgvector Similarity**: Uses 384-dimensional embeddings with HNSW indexing
- **CATVER Integration**: Full support for Mexican insurance CATVER format
- **Structured Labels**: Fixed-order labels matching catalog format

### 📊 Processing Features
- **Semantic Search**: Real pgvector similarity with `<=>` operator
- **Hybrid Scoring**: 70% embedding + 30% fuzzy string matching
- **Decision Thresholds**: auto_accept (≥0.90), needs_review (≥0.70), no_match
- **Active Catalog**: Automatically uses ACTIVE catalog version from database

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL with pgvector extension
- OpenAI API key
- Docker (optional)

### Environment Setup
```bash
# Required environment variables
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql+psycopg://minca:minca@db:5432/minca
DEBUG=true
LOG_LEVEL=INFO
```

### Running with Docker Compose
```bash
# From project root
docker-compose up vehicle-codifier
```

The service will be available at `http://localhost:8002`

### Running Locally
```bash
cd services/vehicle-codifier
poetry install

# Simple way
python run_service.py

# Or with uvicorn directly
poetry run uvicorn vehicle_codifier.main:app --host 0.0.0.0 --port 8002 --reload
```

### Testing
```bash
python test_service.py
```

## 📖 API Endpoints

### Direct Vehicle Matching
#### Single Vehicle Match
```bash
curl -X POST "http://localhost:8002/match" \
  -H "Content-Type: application/json" \
  -d '{
    "modelo": 2020,
    "description": "toyota yaris sol l 4 cilindros"
  }'
```

#### Batch Vehicle Match
```bash
curl -X POST "http://localhost:8002/match/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicles": [
      {"modelo": 2020, "description": "toyota yaris sol l"},
      {"modelo": 2019, "description": "honda civic ex"}
    ]
  }'
```

### Database Integration (Main API)

#### Batch Codification (Database-Driven)
```bash
# Process existing run
curl -X POST "http://localhost:8002/codify/batch?run_id=existing-run-id"

# Create new run
curl -X POST "http://localhost:8002/codify/batch?case_id=test-case"
```

### Monitoring Endpoints

#### Health Check
```bash
curl http://localhost:8002/health
```

#### Service Metrics
```bash
curl http://localhost:8002/metrics
```

## 🔧 Configuration

### Processing Configuration
```python
# In settings.py
max_batch_size: int = 200
max_concurrent_requests: int = 50
confidence_threshold: float = 0.8
```

### Decision Thresholds
```python
# Default thresholds
T_HIGH = 0.90  # Auto-accept threshold
T_LOW = 0.70   # Needs review threshold
```

### CATVER Label Processing
```python
# Structured label format used for matching
label_format = """
modelo=<year> | marca=<brand> | submarca=<model> | numver=<numver> | ramo=<ramo> | cvemarc=<cvemarc> | cvesubm=<cvesubm> | martip=<martip> | cvesegm=<segment> | descveh=<description> | idperdiod=<period> | sumabas=<sum> | tipveh=<vehicle_type>
"""

# Example structured label
label_example = "modelo=2020 | marca=toyota | submarca=yaris | numver=2002 | ramo=711 | cvemarc=47 | cvesubm=1245 | martip=615 | cvesegm=compacto | descveh=yaris sol l 4 cilindros | idperdiod=202002 | sumabas=195000.0 | tipveh=auto"
```

## 🧪 Response Format

### Match Result
```json
{
  "success": true,
  "decision": "auto_accept",
  "confidence": 0.92,
  "suggested_cvegs": 1234567890,
  "candidates": [
    {
      "cvegs": 1234567890,
      "marca": "toyota",
      "submarca": "yaris",
      "modelo": 2020,
      "descveh": "yaris sol l 4 cilindros",
      "label": "modelo=2020 | marca=toyota | submarca=yaris | cvesegm=compacto | descveh=yaris sol l 4 cilindros | tipveh=auto",
      "similarity_score": 0.89,
      "fuzzy_score": 0.95,
      "final_score": 0.92
    }
  ],
  "extracted_fields": {
    "marca": "toyota",
    "submarca": "yaris",
    "cvesegm": "compacto",
    "descveh": "toyota yaris sol l 4 cilindros",
    "tipveh": "auto"
  },
  "processing_time_ms": 156.3,
  "query_label": "modelo=2020 | marca=toyota | submarca=yaris | cvesegm=compacto | descveh=toyota yaris sol l 4 cilindros | tipveh=auto"
}
```

### Batch Processing Result
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

## 🔍 Architecture Benefits

### Clean Architecture Advantages
- **Testable**: Easy unit testing with dependency injection
- **Maintainable**: Clear separation of concerns
- **Extensible**: Easy to add new features without breaking existing code
- **Framework Independent**: Business logic isolated from external frameworks

### Performance Optimizations
- **Singleton Services**: Domain services instantiated once and reused
- **Repository Caching**: Automatic dataset caching with warm-up
- **Chunked Processing**: Optimal batch processing with configurable sizes
- **Controlled Concurrency**: Semaphore-based request limiting

## 🛠️ Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

### Adding New Features
Follow the Clean Architecture pattern:
1. Define domain entities in `domain/entities/`
2. Create use cases in `application/use_cases/`
3. Implement repositories in `infrastructure/repositories/`
4. Add API controllers in `presentation/controllers/`

## 🔗 Integration

This service integrates with:
- **Main API Service**: Via `/codify/batch` endpoint calls
- **Database Package**: For persistence and migrations
- **ML Package**: For text normalization and embeddings
- **Schemas Package**: For data validation

## 🐳 Docker

### Building the Image
```bash
docker build -t vehicle-codifier .
```

### Running the Container
```bash
docker run -p 8002:8002 \
  -e OPENAI_API_KEY=your_key \
  -e DATABASE_URL=your_db_url \
  vehicle-codifier
```

## 📄 License

Private - Minca Insurance AI Platform

---

**Minca AI** - Unified Vehicle Codification with Clean Architecture 🚗🤖