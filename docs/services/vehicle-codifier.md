# Vehicle Codifier Service Documentation

The Vehicle Codifier Service is a unified, AI-powered vehicle matching and AMIS/CVEGS codification service that combines sophisticated vehicle matching with ML-driven classification. Built using Clean Architecture principles with Domain-Driven Design.

## Service Overview

### **Purpose**
- Match vehicle descriptions to AMIS/CVEGS codes using hybrid AI approach
- Process single vehicles or batches with high accuracy
- Provide dual-mode operation: real-time API + background worker
- Support multiple insurance companies with configurable datasets

### **Technology Stack**
- **Framework**: FastAPI (Python 3.11+)  
- **Architecture**: Clean Architecture + Domain-Driven Design
- **AI/ML**: OpenAI GPT models + sentence-transformers + pgvector
- **Database**: PostgreSQL with pgvector extension
- **Data Processing**: pandas, numpy, rapidfuzz
- **Validation**: Pydantic models with comprehensive schemas

### **Port**: 8002 (configurable)

## Architecture Overview

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                 Presentation Layer                      │
│              (FastAPI Controllers)                     │
├─────────────────────────────────────────────────────────┤
│                 Application Layer                       │
│                  (Use Cases)                           │
├─────────────────────────────────────────────────────────┤
│                   Domain Layer                          │
│         (Entities, Value Objects, Services)            │
├─────────────────────────────────────────────────────────┤
│               Infrastructure Layer                      │
│          (Repositories, Adapters, External)            │
└─────────────────────────────────────────────────────────┘
```

### Key Components

#### **Domain Layer**
- **Entities**: Vehicle, CVEGSEntry, MatchResult with rich behavior
- **Value Objects**: VehicleAttributes, ConfidenceScore, MatchCriteria
- **Domain Services**: AttributeExtractor, CandidateFinder, ScoringEngine

#### **Application Layer**  
- **Use Cases**: MatchSingleVehicle, MatchVehicleBatch
- **Workflow Orchestration**: Complex business logic coordination

#### **Infrastructure Layer**
- **Repositories**: CVEGSRepository with caching and query optimization
- **Adapters**: LLM integration, data loading, external service integration

#### **Worker Module**
- **Background Processing**: Database-driven batch codification
- **Legacy Integration**: Compatible with existing API service calls

## Key Features

### 🎯 **Dual Processing Modes**
- **Web API**: Real-time vehicle matching via REST endpoints
- **Background Worker**: Database-driven batch processing for high-volume tasks

### 🤖 **Advanced AI Matching**
- **Hybrid Scoring**: 70% embeddings + 30% fuzzy matching  
- **Multi-stage Pipeline**: Exact → Fuzzy → Semantic → LLM tie-breaking
- **Confidence Scoring**: Three-tier decisions (auto_accept, needs_review, no_match)

### 📊 **Excel Integration**
- **Native Column Support**: Spanish Excel headers (Marca, Submarca, Año, etc.)
- **High Confidence Data**: Excel data takes precedence over LLM extraction
- **Intelligent Mapping**: 80+ column synonyms with smart detection

### 🔄 **Batch Processing**
- **Chunked Parallel Processing**: Configurable batch sizes (default 50 per chunk)
- **Controlled Concurrency**: Semaphore-based request limiting  
- **Progress Tracking**: Real-time status monitoring and metrics

## API Endpoints

### Vehicle Matching

#### `POST /match` - Unified Vehicle Matching
Handles both single vehicles and batch requests with automatic detection.

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
}
```

**Enhanced Response:**
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
      "extracted_attributes": {
        "brand": "TOYOTA",
        "model": "YARIS",
        "year": 2020,
        "fuel_type": "GASOLINE",
        "body_style": "HATCHBACK"
      },
      "processing_time_ms": 245.7,
      "candidates": [
        {
          "cvegs": "1234567890",
          "score": 0.92,
          "label": "toyota yaris 2020 hatchback particular"
        }
      ]
    }
  ],
  "summary": {
    "total_vehicles": 2,
    "successful_matches": 2,
    "success_rate": 100.0,
    "confidence_distribution": {
      "high_confidence": 2,
      "medium_confidence": 0,
      "low_confidence": 0
    }
  }
}
```

### Background Processing

#### `POST /codify/batch` - Database-Driven Codification
Process existing database runs for batch codification.

**Parameters:**
- `run_id` (optional): Existing run ID to process
- `case_id` (optional): Case ID for new runs

**Response:**
```json
{
  "run_id": "uuid-v4",
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

### Dataset Management

#### `GET /datasets/stats` - Dataset Statistics
Get comprehensive statistics about loaded AMIS datasets.

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

#### `POST /insurers/{insurer_id}/initialize` - Initialize Insurer
Load and cache dataset for specific insurer.

### Monitoring

#### `GET /health` - Health Check
Enhanced health check with Clean Architecture status.

```json
{
  "status": "healthy",
  "timestamp": "2024-09-15T14:30:22.123456",
  "version": "1.0.0",
  "dataset_loaded": true,
  "dataset_records": 50000,
  "openai_available": true
}
```

#### `GET /metrics` - Service Metrics
Comprehensive metrics including Clean Architecture information.

```json
{
  "service_info": {
    "name": "Vehicle Codifier Service",
    "architecture": "Clean Architecture with Domain-Driven Design",
    "features": {
      "ai_powered_matching": true,
      "batch_processing": true,
      "excel_integration": true,
      "clean_architecture": true
    }
  },
  "clean_architecture": {
    "enabled": true,
    "services": {
      "total_registered": 12,
      "singleton_instances": 8,
      "container_status": "healthy"
    }
  },
  "performance_optimizations": {
    "repository_caching": true,
    "chunked_batch_processing": true,
    "controlled_concurrency": true
  }
}
```

## Configuration

### Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.1

# Database Configuration  
DATABASE_URL=postgresql+psycopg://minca:minca@db:5432/minca

# Processing Configuration
MAX_BATCH_SIZE=200
MAX_CONCURRENT_REQUESTS=50
CONFIDENCE_THRESHOLD=0.8

# Service Configuration
DEBUG=true
LOG_LEVEL=INFO
```

### Decision Thresholds

```python
# Confidence scoring thresholds
T_HIGH = 0.90  # Auto-accept threshold
T_LOW = 0.70   # Needs review threshold

# Below T_LOW = no_match
```

### Excel Column Mapping

```python
# Supported Spanish Excel columns with high confidence
COLUMN_MAPPING = {
    "Marca": "brand",           # Confidence: 0.95
    "Submarca": "model",        # Confidence: 0.95  
    "Año MOdelos": "year",      # Confidence: 0.95
    "Descripcion": "description", # Always required
    "SERIE": "vin",             # Optional
    "Paquete De Cobert": "coverage_package"  # Optional
}
```

## Performance Characteristics

### Benchmarks
- **Single Vehicle Matching**: ~250ms average
- **Batch Processing**: ~200ms per vehicle (parallel)
- **Cache Hit Rate**: >95% after warm-up
- **Success Rate**: 85-95% depending on data quality

### Optimizations
- **Singleton Services**: Domain services instantiated once
- **Repository Caching**: Automatic dataset caching with warm-up
- **Chunked Processing**: Optimal batch sizes (50 vehicles per chunk)
- **Controlled Concurrency**: Semaphore-based limiting (10 concurrent max)

## Integration

### With Main API Service
```python
# Main API calls vehicle-codifier for batch processing
from vehicle_codifier.worker.main import process_run
process_run(run_id)
```

### With Database Layer
```python
# Uses shared models from packages/db
from app.db.models import Run, Row, Codify
```

### With ML Package
```python
# Leverages shared ML utilities
from app.ml.retrieve import VehicleRetriever
from app.ml.normalize import normalize_text
```

## Development

### Running the Service

**With Docker:**
```bash
docker-compose up vehicle-codifier
```

**Locally:**
```bash
cd services/vehicle-codifier
poetry install
poetry run uvicorn vehicle_codifier.main:app --reload --port 8002
```

### Testing

```bash
# Unit tests (domain layer)
pytest tests/domain/ -v

# Integration tests (use cases)
pytest tests/application/ -v

# API tests (presentation layer)  
pytest tests/presentation/ -v

# All tests with coverage
pytest --cov=vehicle_codifier --cov-report=html
```

### Code Quality

```bash
# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## Troubleshooting

### Common Issues

**OpenAI API Errors:**
- Verify `OPENAI_API_KEY` is set correctly
- Check API rate limits and quotas
- Monitor API response times

**Database Connection Issues:**
- Verify `DATABASE_URL` format and credentials
- Check PostgreSQL service status
- Ensure pgvector extension is installed

**Performance Issues:**
- Monitor batch processing chunk sizes
- Check concurrent request limits
- Review cache hit rates in metrics

**Import Errors:**
- Verify `PYTHONPATH` includes packages directories
- Check Poetry workspace configuration
- Ensure all dependencies are installed

### Debug Mode

```bash
# Enable detailed logging
DEBUG=true
LOG_LEVEL=DEBUG

# Enable SQL query logging  
DATABASE_ECHO=true
```

## Architecture Benefits

### Clean Architecture Advantages
- **Testable**: Easy unit testing with dependency injection
- **Maintainable**: Clear separation of concerns
- **Extensible**: Easy to add features without breaking existing code
- **Framework Independent**: Business logic isolated from FastAPI

### Domain-Driven Design Benefits
- **Business-Focused**: Code reflects business domain concepts
- **Expressive**: Rich domain models with meaningful behavior
- **Maintainable**: Business logic centralized in domain layer
- **Scalable**: Modular design supports growth

## Future Enhancements

- **Redis Caching**: Distributed caching for multi-instance deployments
- **Real-time Streaming**: WebSocket support for live processing updates  
- **Advanced ML Models**: Custom fine-tuned models for specific insurers
- **Multi-language Support**: Support for additional languages beyond Spanish
- **Audit Trail**: Comprehensive matching decision audit logging

---

This service represents the evolution of vehicle codification with modern architecture patterns, providing both high performance and maintainability for the Minca AI Insurance Platform.