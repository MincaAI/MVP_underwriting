# Vehicle Codifier Service

A unified vehicle codification service that combines sophisticated vehicle matching with ML-powered AMIS/CVEGS code classification. This service consolidates the functionality of the previous `vehicle-matcher` and `worker-codifier` services into a single, well-architected solution.

## 🏗️ Architecture

Built using **Clean Architecture** principles with **Domain-Driven Design**:

```
vehicle-codifier/
├── src/vehicle_codifier/
│   ├── domain/              # Business logic (entities, value objects, services)
│   ├── application/         # Use cases and workflows
│   ├── infrastructure/      # External concerns (repositories, adapters)
│   ├── presentation/        # API controllers
│   ├── worker/             # Background processing logic
│   ├── models/             # Pydantic models
│   ├── services/           # Legacy services
│   ├── config/             # Configuration
│   └── main.py            # FastAPI application
├── Dockerfile
├── pyproject.toml
└── README.md
```

## ✨ Key Features

### 🎯 Dual Processing Modes
- **Web API**: Real-time vehicle matching with FastAPI
- **Background Worker**: Database-driven batch processing

### 🤖 Advanced Matching
- **Clean Architecture**: Domain-driven design with strict separation of concerns
- **AI-Powered**: OpenAI GPT models for intelligent attribute extraction
- **High Accuracy**: Multi-stage matching with confidence scoring (85%+ success rate)
- **CATVER Integration**: Full support for Mexican insurance CATVER format (14 columns)
- **Structured Labels**: Uses fixed-order label format for consistent embeddings

### 📊 Processing Features
- **Batch Processing**: Chunked parallel processing (configurable batch sizes)
- **Semantic Search**: 384-dimensional embeddings with pgvector (intfloat/multilingual-e5-small)
- **Reranking**: Hybrid scoring (70% embeddings + 30% fuzzy matching)
- **Decision Engine**: Three-tier decisions (auto_accept, needs_review, no_match)
- **CATVER Compliance**: Works with structured labels containing all CATVER fields

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
poetry run uvicorn vehicle_codifier.main:app --host 0.0.0.0 --port 8002 --reload
```

## 📖 API Endpoints

### Vehicle Matching API (Batch Only)
#### Batch Vehicle Match
```bash
curl -X POST "http://localhost:8002/match" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicles": [
      {
        "description": "TOYOTA YARIS SOL L 2020",
        "brand": "TOYOTA",
        "model": "YARIS",
        "year": 2020
      },
      {
        "description": "HONDA CIVIC EX 2019",
        "brand": "HONDA",
        "model": "CIVIC",
        "year": 2019
      }
    ],
    "insurer_id": "default",
    "parallel_processing": true
  }'
```

### Worker Processing API

#### Batch Codification (Database-Driven)
```bash
curl -X POST "http://localhost:8002/codify/batch?run_id=existing-run-id"
# or create new run
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
  "cvegs_code": "1234567890",
  "confidence_score": 0.92,
  "confidence_level": "high",
  "matched_brand": "TOYOTA",
  "matched_model": "YARIS",
  "matched_year": 2020,
  "extracted_attributes": {
    "brand": "TOYOTA",
    "model": "YARIS",
    "year": 2020,
    "fuel_type": "GASOLINE",
    "body_style": "HATCHBACK"
  },
  "processing_time_ms": 245.7,
  "match_method": "clean_architecture_enhanced",
  "candidates": [
    {
      "cvegs": "1234567890",
      "score": 0.92,
      "label": "modelo=2020 | marca=toyota | submarca=yaris | numver=2002 | ramo=711 | cvemarc=47 | cvesubm=1245 | martip=615 | cvesegm=compacto | descveh=yaris sol l 4 cilindros | idperdiod=202002 | sumabas=195000.0 | tipveh=auto"
    }
  ]
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