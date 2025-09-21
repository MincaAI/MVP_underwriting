# Vehicle Codifier Service Documentation

## Overview

The Vehicle Codifier Service is a modular, high-performance system that matches vehicle descriptions to standardized CATVER (Catalog of Vehicles) codes using machine learning, fuzzy matching, and configurable filtering strategies.

## Key Features

- **🔧 VIN Removal**: Automatic removal of VIN numbers during preprocessing
- **🎯 High-Confidence Filtering**: Configurable filtering based on confidence scores
- **🤖 LLM Integration**: OpenAI GPT-4o-mini for intelligent field extraction
- **📊 Vector Similarity**: pgvector-based semantic matching
- **⚡ Performance Optimized**: In-memory caching and parallel processing
- **🔄 Modular Architecture**: Separated concerns for maintainability

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL with pgvector extension
- OpenAI API key (optional, for LLM features)

### Installation

```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your database and API credentials

# Run the service
python run_service.py
```

### Basic Usage

```bash
# Health check
curl http://localhost:8002/health

# Match a vehicle
curl -X POST http://localhost:8002/match \
  -H "Content-Type: application/json" \
  -d '{"0": {"modelo": 2019, "description": "TRACTO FREIGHTLINER CASCADIA"}}'
```

## Architecture

### Modular Components

The system is built with a modular architecture for better maintainability:

```
src/vehicle_codifier/
├── service.py              # Main orchestration service (169 lines, was 944)
├── preprocessor.py         # Input preprocessing with VIN removal
├── extractor.py           # Field extraction with confidence scoring
├── candidate_filter.py    # High-confidence filtering
├── candidate_matcher.py   # Hybrid matching (cache + database)
├── llm_validator.py       # LLM-based validation
├── decision_engine.py     # Decision logic
├── models.py              # Pydantic data models
└── config.py              # Configuration settings
```

### Data Flow

```
Input Description
    ↓
[Preprocessor] ← VIN Removal
    ↓
[Extractor] ← Field Extraction with Confidence
    ↓
[High-Confidence Filter] ← Direct SQL filtering (≥0.9 confidence)
    ↓
[Candidate Matcher] ← Hybrid search (cache/database)
    ↓
[LLM Validator] ← OpenAI validation with preservation
    ↓
[Decision Engine] ← auto_accept/needs_review/no_match
    ↓
Final Result
```

## Recent Changes

### VIN Removal Implementation
- **Mandatory VIN removal** in preprocessing step
- **Pattern**: `[A-HJ-NPR-Z0-9]{17}` (excludes I, O, Q per VIN standards)
- **Performance**: <1ms overhead
- **Coverage**: All VIN positions (start, middle, end, multiple)

### Configurable Filtering
- **High-confidence threshold**: Configurable in `config.py` (default: 0.9)
- **Dynamic filtering**: Based on extracted field confidence scores
- **Direct SQL filtering**: Bypasses embedding search for high-confidence matches

### Modular Refactoring
- **82% code reduction** in main service.py (944 → 169 lines)
- **Separated concerns**: Each component has single responsibility
- **Improved testability**: Individual component testing
- **Better maintainability**: Clear module boundaries

## Documentation Index

- [Architecture](./architecture.md) - Detailed system architecture
- [API Reference](./api.md) - Complete API documentation
- [Configuration](./configuration.md) - Configuration options
- [Preprocessing](./preprocessing.md) - Text preprocessing and VIN removal
- [Field Extraction](./field-extraction.md) - LLM-based field extraction
- [Matching Pipeline](./matching-pipeline.md) - Candidate matching process
- [Testing](./testing.md) - Testing strategies and test suite
- [Performance](./performance.md) - Performance optimization guide
- [Deployment](./deployment.md) - Deployment instructions

## Performance Metrics

- **Preprocessing**: ~0.1ms average (VIN removal)
- **Field Extraction**: ~3000ms average (LLM calls)
- **High-Confidence Filtering**: Direct SQL, ~100ms
- **Vector Matching**: ~500ms (cached), ~2000ms (database)
- **Total Pipeline**: ~3500ms average

## Configuration

Key configuration options in `config.py`:

```python
# High-confidence filtering threshold
high_confidence_threshold: float = 0.9

# VIN removal (always enabled)
# Pattern: r'\b[A-HJ-NPR-Z0-9]{17}\b'

# Decision thresholds by vehicle type
thresholds_by_type: Dict[str, Dict[str, float]] = {
    "auto": {"high": 0.90, "low": 0.70},
    "camioneta": {"high": 0.75, "low": 0.55},
    "motocicleta": {"high": 0.85, "low": 0.65},
}

# Reranking weights (optimized for trusted year input)
weight_embedding: float = 0.40
weight_fuzzy: float = 0.20
weight_brand_match: float = 0.10
weight_year_proximity: float = 0.25
weight_type_match: float = 0.05
```

## Testing

Run the comprehensive test suite:

```bash
# Full test suite with VIN validation
python test_custom.py

# Covers:
# - VIN removal validation
# - Pipeline integration
# - Performance benchmarking
# - API validation
# - Edge case handling
```

## Support

For questions or issues:
1. Check the [documentation](./README.md)
2. Run the test suite to validate setup
3. Review configuration settings
4. Check service logs for debugging

## Version History

- **v0.2.0-simplified**: Modular architecture, VIN removal, configurable filtering
- **v0.1.0**: Initial monolithic implementation