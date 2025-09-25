# Vehicle Codifier Service - Simplified

A clean, simplified vehicle codification service that provides CVEGS matching using pgvector similarity search.

## 📁 Clean Structure

```
vehicle-codifier/
├── src/vehicle_codifier/
│   ├── main.py              # FastAPI app (298 lines)
│   ├── service.py           # Core orchestration (157 lines)
│   ├── processor.py         # Unified extraction + embeddings (350+ lines)
│   ├── models.py            # Data models (116 lines)
│   ├── config.py            # Settings (119 lines)
│   ├── utils.py             # Utilities (73 lines)
│   ├── preprocessor.py      # Input preprocessing (349 lines)
│   ├── candidate_filter.py  # Search filtering (209 lines)
│   ├── candidate_matcher.py # Candidate matching (372 lines)
│   ├── cache.py             # Catalog caching (345 lines)
│   ├── decision_engine.py   # Decision logic (104 lines)
│   ├── llm_validator.py     # LLM validation (178 lines)
│   ├── brand_lookup.py      # Brand utilities (206 lines)
│   └── __init__.py          # Package init
├── tests/
│   └── test_service.py      # Basic integration test
├── docs/                    # Documentation
├── run_service.py           # Service runner
├── pyproject.toml
├── Dockerfile
└── README.md

TOTAL: 14 core files (~2,900 lines vs 3,346 before cleanup)
```

## 🔄 Key Improvements Made

### ✅ **Removed Clutter** (45+ files eliminated):
- All `.bak` backup files
- 25+ redundant test files (`test_*`)
- Debug scripts (`debug_*`)
- Check scripts (`check_*`)
- Benchmark files and results
- Duplicate documentation files

### ✅ **Unified Components**:
- **VehicleProcessor**: Combines field extraction + embedding generation (replaces VehicleExtractor + VehicleLabelBuilder)
- **Simplified Service**: Direct orchestration instead of complex pipeline
- **Organized Tests**: Moved to `/tests` directory

### ✅ **Architecture Cleanup**:
- Single responsibility per module
- Eliminated redundant embedding logic
- Cleaner import structure
- Consistent error handling

## 🚀 Quick Start

```bash
cd services/vehicle-codifier
poetry install
poetry run python run_service.py
```

**Service URL**: http://localhost:8002
**API Docs**: http://localhost:8002/docs

## 📝 API Usage

```bash
curl -X POST "http://localhost:8002/match" \
  -H "Content-Type: application/json" \
  -d '{
    "0": {"modelo": 2022, "description": "INTERNATIONAL TRACTO"},
    "1": {"modelo": 2019, "description": "KENWORTH T 800"}
  }'
```

## 🧪 Testing

```bash
cd tests
poetry run python test_service.py
```

---

**Result**: Clean, maintainable codebase with 74% fewer files and improved organization.