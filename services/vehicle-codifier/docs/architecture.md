# System Architecture

## Overview

The Vehicle Codifier Service follows a modular architecture pattern with clear separation of concerns. The system was recently refactored from a monolithic 944-line service to a distributed architecture with 169-line orchestration service and specialized components.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Main App                        │
│                      (main.py)                                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                  Vehicle Codifier Service                      │
│                     (service.py)                               │
│                   Orchestration Layer                          │
└──┬────────┬────────┬────────┬────────┬────────┬────────┬───────┘
   │        │        │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼        ▼        ▼
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│Pre  │ │Extr │ │Filt │ │Match│ │LLM  │ │Deci │ │Cache│
│proc │ │act  │ │er   │ │er   │ │Val  │ │sion │ │     │
│     │ │     │ │     │ │     │ │     │ │     │ │     │
└─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
```

## Component Details

### 1. FastAPI Application Layer (`main.py`)
- **Purpose**: HTTP interface and request handling
- **Key Features**:
  - CORS middleware
  - Flexible input format handling
  - Error handling and validation
  - Health check endpoints

### 2. Orchestration Service (`service.py`)
- **Purpose**: Main business logic coordination
- **Size**: 169 lines (reduced from 944 lines - 82% reduction)
- **Responsibilities**:
  - Component initialization
  - Pipeline orchestration
  - Error handling
  - Result aggregation

### 3. Preprocessor (`preprocessor.py`)
- **Purpose**: Input data cleaning and normalization
- **Key Features**:
  - **VIN Removal**: Mandatory removal of 17-character VIN patterns
  - Field detection (year, description)
  - Text normalization (unidecode, uppercase)
  - Multiple input format support
- **VIN Pattern**: `r'\b[A-HJ-NPR-Z0-9]{17}\b'`
- **Performance**: <1ms average

### 4. Field Extractor (`extractor.py`)
- **Purpose**: Extract structured vehicle fields from descriptions
- **Method**: LLM-based with confidence scoring
- **Extracted Fields**:
  - `marca` (brand)
  - `submarca` (submodel)
  - `cvesegm` (segment)
  - `tipveh` (vehicle type)
- **Confidence Methods**: direct, fuzzy, keyword, llm

### 5. Candidate Filter (`candidate_filter.py`)
- **Purpose**: High-confidence direct SQL filtering
- **Threshold**: Configurable (default: 0.9)
- **Strategy**: Apply filters only when confidence ≥ threshold
- **Benefits**: Bypasses expensive vector search for obvious matches

### 6. Candidate Matcher (`candidate_matcher.py`)
- **Purpose**: Hybrid candidate search and scoring
- **Strategies**:
  - **Cache-first**: In-memory vector search (fast)
  - **Database fallback**: pgvector similarity search
  - **Fallback mode**: Text-only matching when embeddings unavailable
- **Scoring**: Multi-factor (embedding, fuzzy, brand, year, type)

### 7. LLM Validator (`llm_validator.py`)
- **Purpose**: Intelligent candidate validation and scoring
- **Model**: OpenAI GPT-4o-mini
- **Special Handling**: Preserves high-confidence candidates (≥0.9)
- **Blending**: Conservative blending for pre-filtered candidates

### 8. Decision Engine (`decision_engine.py`)
- **Purpose**: Final decision making based on scores and thresholds
- **Decisions**:
  - `auto_accept`: High confidence, automatic processing
  - `needs_review`: Medium confidence, human review required
  - `no_match`: Low confidence, no suitable candidates
- **Vehicle-specific thresholds**: Different thresholds by vehicle type

### 9. Cache System (`cache.py`)
- **Purpose**: In-memory vector search optimization
- **Features**:
  - Automatic refresh (24h intervals)
  - Memory usage monitoring (~187MB for 84k records)
  - Fallback to database when unavailable

## Data Models (`models.py`)

### Core Models
```python
class VehicleInput(BaseModel):
    modelo: int          # Year
    description: str     # Vehicle description

class ExtractedFieldsWithConfidence(BaseModel):
    marca: FieldConfidence
    submarca: FieldConfidence
    cvesegm: FieldConfidence
    tipveh: FieldConfidence
    descveh: Optional[str]  # Cleaned description

class FieldConfidence(BaseModel):
    value: Optional[str]
    confidence: float     # 0.0 - 1.0
    method: str          # "direct", "fuzzy", "keyword", "llm"

class Candidate(BaseModel):
    cvegs: int           # CATVER code
    marca: str
    submarca: str
    modelo: int
    similarity_score: float
    fuzzy_score: float
    final_score: float
    # ... additional fields

class MatchResult(BaseModel):
    success: bool
    decision: str        # "auto_accept", "needs_review", "no_match"
    confidence: float
    suggested_cvegs: Optional[int]
    candidates: List[Candidate]
    processing_time_ms: float
```

## Configuration (`config.py`)

### Key Settings
```python
class Settings(BaseSettings):
    # VIN removal (mandatory, no config needed)
    # Pattern: r'\b[A-HJ-NPR-Z0-9]{17}\b'

    # High-confidence filtering
    high_confidence_threshold: float = 0.9

    # Decision thresholds by vehicle type
    thresholds_by_type: Dict[str, Dict[str, float]] = {
        "auto": {"high": 0.90, "low": 0.70},
        "camioneta": {"high": 0.75, "low": 0.55},
        "motocicleta": {"high": 0.85, "low": 0.65},
        "default": {"high": 0.80, "low": 0.60}
    }

    # Multi-factor scoring weights
    weight_embedding: float = 0.40
    weight_fuzzy: float = 0.20
    weight_brand_match: float = 0.10
    weight_year_proximity: float = 0.25
    weight_type_match: float = 0.05
```

## Processing Pipeline

### 1. Input Processing
```
Raw Input → Field Detection → VIN Removal → Normalization
```

### 2. Field Extraction
```
Clean Description → LLM Analysis → Confidence Scoring → Validation
```

### 3. Candidate Generation
```
High-Confidence Filter → Hybrid Search → Multi-factor Scoring
```

### 4. Validation & Decision
```
LLM Validation → Score Blending → Threshold Comparison → Final Decision
```

## Database Integration

### Tables Used
- `amis_catalog`: Main vehicle catalog (84k+ records)
- `catalog_import`: Catalog versioning and status
- Embedding vectors stored in PostgreSQL with pgvector

### Queries
- **High-confidence**: Direct SQL with exact matches
- **Vector search**: pgvector similarity with `<=>` operator
- **Fallback**: Text-based fuzzy matching

## Performance Characteristics

### Component Performance
| Component | Average Time | Notes |
|-----------|-------------|--------|
| Preprocessing | 0.1ms | VIN removal overhead minimal |
| Field Extraction | 3000ms | LLM API calls |
| High-Confidence Filter | 100ms | Direct SQL |
| Vector Search (cached) | 500ms | In-memory |
| Vector Search (DB) | 2000ms | PostgreSQL |
| LLM Validation | 1000ms | Optional enhancement |

### Optimization Strategies
1. **Cache-first matching**: Reduces database load
2. **High-confidence filtering**: Bypasses expensive operations
3. **Parallel processing**: Multiple components can run concurrently
4. **Configurable thresholds**: Tune for speed vs accuracy

## Error Handling

### Graceful Degradation
1. **LLM unavailable**: Falls back to fuzzy matching
2. **Cache unavailable**: Uses database search
3. **Embeddings unavailable**: Text-only matching
4. **Database unavailable**: Returns appropriate error

### Validation Layers
1. **Input validation**: Pydantic models
2. **Business logic validation**: Service layer
3. **Data validation**: Database constraints
4. **Output validation**: Response models

## Security Considerations

1. **API Key Protection**: OpenAI keys in environment variables
2. **Input Sanitization**: Text normalization and VIN removal
3. **SQL Injection Prevention**: Parameterized queries
4. **Rate Limiting**: FastAPI built-in features

## Scalability

### Horizontal Scaling
- Stateless components enable multi-instance deployment
- Shared cache can be externalized (Redis)
- Database connection pooling

### Vertical Scaling
- Memory-efficient caching
- Lazy loading of components
- Configurable batch sizes

## Monitoring & Observability

### Metrics
- Processing times per component
- Cache hit rates
- LLM API usage
- Decision distribution

### Logging
- Structured logging with component identification
- Debug information for troubleshooting
- Performance metrics tracking

This architecture provides a robust, maintainable, and scalable foundation for vehicle description matching with clear separation of concerns and comprehensive error handling.