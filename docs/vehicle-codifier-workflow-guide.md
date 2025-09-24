# Vehicle Codifier Workflow Guide

> **Comprehensive documentation of the vehicle codification process logic and pipeline**

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Detailed Workflow Steps](#detailed-workflow-steps)
4. [Configuration & Settings](#configuration--settings)
5. [Performance Metrics](#performance-metrics)
6. [Debugging & Troubleshooting](#debugging--troubleshooting)
7. [Code References](#code-references)

---

## Overview

The Vehicle Codifier is a sophisticated AI-powered system that matches vehicle descriptions to standardized AMIS (Mexican vehicle classification) codes. It processes vehicle information through a 6-step pipeline combining rule-based logic, machine learning, and large language models.

### 🎯 **Primary Goal**
Convert free-text vehicle descriptions like `"TRACTO TR FREIGHTLINER CASCADIA DD16 510 STD"` into standardized CVEGS codes from the AMIS catalog.

### 📊 **Performance Benchmarks**
- **Top-3 Accuracy**: 94.7% (correct AMIS in top 3 results)
- **Top-1 Accuracy**: 63.2% (exact match in first position)  
- **Processing Time**: ~1.6 seconds average
- **Success Rate**: 100% (no system failures)

---

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Input Data    │ -> │  Preprocessing  │ -> │ Field Extraction│
│ año: 2022       │    │ - Normalization │    │ - Marca         │
│ desc: "TRACTO"  │    │ - VIN removal   │    │ - Submarca      │
└─────────────────┘    │ - Text cleanup  │    │ - Tipveh        │
                       └─────────────────┘    └─────────────────┘
                                                         |
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Final Decision  │ <- │ Score Mixing &  │ <- │   Candidate     │
│ - Auto Accept   │    │ LLM Finalizer   │    │   Filtering     │
│ - Needs Review  │    │ - Weight scores │    │ - High Conf.    │
│ - No Match      │    │ - LLM rerank    │    │ - Fallback      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                         |
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Embedding &     │ <- │   Fuzzy &       │
                       │ Similarity      │    │   Matching      │
                       │ - Semantic      │    │ - String match  │
                       │ - Vector search │    │ - Ratio scoring │
                       └─────────────────┘    └─────────────────┘
```

### 🏗️ **Key Components**

| Component | Purpose | File Location |
|-----------|---------|---------------|
| **VehicleCodeifier** | Main orchestrator | `core/service.py` |
| **VehiclePreprocessor** | Input normalization | `pipeline/preprocessor.py` |
| **FieldExtractor** | Extract marca/submarca/tipveh | `pipeline/field_extractor.py` |
| **CandidateFilter** | AMIS catalog filtering | `search/candidate_filter.py` |
| **DecisionEngine** | Final decision logic | `pipeline/decision_engine.py` |

---

## Detailed Workflow Steps

### 🔄 **Step 1: Input Preprocessing**
**File**: `pipeline/preprocessor.py`  
**Purpose**: Normalize and clean input data for consistent processing

#### **Process**:
1. **Field Detection**: Automatically identify year and description fields from input data
2. **Text Normalization**: Clean and standardize text using `unidecode` 
3. **VIN Removal**: Strip 17-character VIN codes from descriptions
4. **Duplicate Cleanup**: Remove consecutive duplicate words (`"tanque tanque"` → `"tanque"`)
5. **Year Validation**: Ensure year is within valid range (1980-2027)

#### **Input Example**:
```json
{
  "año": 2022,
  "desc": "TRACTO TR FREIGHTLINER NEW CASCADIA DD16 510 STD 3AKJHPDV7NSNC4904"
}
```

#### **Output Example**:
```json
{
  "model_year": 2022,
  "description": "tracto tr freightliner new cascadia dd16 510 std"
}
```

---

### 🎯 **Step 2: Field Extraction with Confidence**
**File**: `pipeline/field_extractor.py`  
**Purpose**: Extract structured vehicle fields (marca, submarca, tipveh) from description

#### **Multi-Stage Extraction Process**:

1. **Stage 1: Direct Substring Matching**
   - Search for exact field values in description
   - Longest-first strategy to avoid conflicts
   - **Confidence**: 1.0 (perfect match)

2. **Stage 2: Fuzzy Matching** 
   - Uses `rapidfuzz` library for approximate matching
   - Combines partial ratio and token sort ratio
   - **Confidence**: 0.4-0.95 based on score

3. **Stage 3: LLM Fallback**
   - OpenAI GPT for complex cases
   - Triggered when overall extraction quality is poor
   - **Confidence**: 0.7-0.9

#### **Conservative Submarca Filtering**:
- **Previous Logic**: Filter submarca when marca confidence ≥ 0.5 (too aggressive)
- **New Logic**: Filter submarca ONLY when marca confidence = 1.0 (perfect match)
- **Benefit**: Preserves candidates like "tanque" when marca extraction is uncertain

#### **Example Debug Output**:
```
[DEBUG] ===== MARCA EXTRACTION =====
[DEBUG] Description: 'tracto tr freightliner cascadia'
[DEBUG] Candidates (56 total): ['freightliner', 'international', ...]
[DEBUG] ✅ DIRECT MATCH FOUND: 'freightliner' found in description
[DEBUG] Final marca result: value='freightliner', confidence=1.000
```

---

### 🔍 **Step 3: High-Confidence Candidate Filtering**  
**File**: `pipeline/filtering.py`  
**Purpose**: Filter AMIS catalog using extracted fields to reduce search space

#### **Filtering Strategy**:

1. **High-Confidence Filtering**:
   ```python
   if marca.confidence >= 0.9:
       filter_by_marca(marca.value)
   if submarca.confidence >= 0.9:
       filter_by_submarca(submarca.value)  
   if tipveh.confidence >= 0.7:
       filter_by_tipveh(tipveh.value)
   ```

2. **Progressive Fallback** (when no candidates found):
   - **Level 1**: Remove tipveh filter
   - **Level 2**: Remove submarca filter  
   - **Level 3**: Remove marca filter
   - **Level 4**: Use year-only filtering

#### **AMIS Catalog Query**:
```sql
SELECT DISTINCT cvegs, marca, submarca, tipveh, modelo
FROM amis_catalog 
WHERE modelo = :year
  AND marca ILIKE :marca_filter
  AND submarca ILIKE :submarca_filter
  AND catalog_version = (SELECT version FROM catalog_import 
                        WHERE status = 'ACTIVE' 
                        ORDER BY version DESC LIMIT 1)
```

---

### 🎲 **Step 4: Fuzzy & Embedding Scoring**
**Files**: `pipeline/fuzzy_matching.py`, `pipeline/embedding_scoring.py`  
**Purpose**: Score candidates using text similarity and semantic matching

#### **Fuzzy Matching**:
- **Algorithm**: RapidFuzz partial ratio and token sort ratio
- **Score Range**: 0.0 - 1.0
- **Implementation**:
  ```python
  fuzzy_score = max(
      fuzz.partial_ratio(description, candidate_text) / 100,
      fuzz.token_sort_ratio(description, candidate_text) / 100
  )
  ```

#### **Embedding Scoring**:
- **Model**: `intfloat/multilingual-e5-large`
- **Method**: Cosine similarity between description and candidate embeddings
- **Score Range**: 0.0 - 1.0
- **Query Label Format**: `"marca submarca modelo tipveh"`

#### **Performance**:
- **Embedding Model Size**: ~2.5GB
- **Vector Dimensions**: 1024
- **Batch Processing**: Up to 32 candidates simultaneously

---

### ⚖️ **Step 5: Score Mixing**
**File**: `core/service.py` (mix_candidate_scores function)  
**Purpose**: Combine multiple scoring methods into final ranking

#### **Weighted Score Formula**:
```python
final_score = (
    0.4 * filter_score +      # Rule-based filtering confidence
    0.3 * fuzzy_score +       # String similarity  
    0.3 * embedding_score     # Semantic similarity
)
```

#### **Score Components**:
- **Filter Score**: Based on field extraction confidence and filtering strength
- **Fuzzy Score**: Text-based similarity using RapidFuzz
- **Embedding Score**: Semantic similarity using transformer embeddings

---

### 🧠 **Step 6: LLM Finalizer & Decision**
**File**: `pipeline/llm_finalizer.py`  
**Purpose**: Final AI-powered reranking and decision making

#### **LLM Finalizer Process**:
1. **Input**: Top 10 candidates by mixed score
2. **Model**: OpenAI GPT-4 or GPT-3.5-turbo  
3. **Context**: Vehicle description + candidate details + extracted fields
4. **Output**: Reranked candidates with LLM confidence scores

#### **Decision Engine Thresholds**:
```python
def make_decision(candidates, confidence_score):
    if confidence_score >= 0.85:
        return "auto_accept"      # High confidence
    elif confidence_score >= 0.60:
        return "needs_review"     # Medium confidence
    else:
        return "no_match"         # Low confidence
```

#### **Decision Categories**:
- **Auto Accept**: Confidence ≥ 85% (production ready)
- **Needs Review**: 60% ≤ Confidence < 85% (human validation)  
- **No Match**: Confidence < 60% (insufficient data)

---

## Configuration & Settings

### 🔧 **Key Settings**
**File**: `config.py`

```python
# Database
DATABASE_URL = "postgresql://user:pass@host:port/database"

# OpenAI Configuration  
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"  # or "gpt-3.5-turbo"

# Year Validation
MIN_VEHICLE_YEAR = 1980
FUTURE_YEARS_AHEAD = 5  # Allow 5 years into future

# Decision Thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.60

# Embedding Model
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DEVICE = "cpu"  # or "cuda" for GPU
```

### 📊 **Performance Tuning**

| Parameter | Default | Impact |
|-----------|---------|--------|
| `HIGH_CONFIDENCE_THRESHOLD` | 0.85 | Higher = fewer auto-accepts, better precision |
| `MEDIUM_CONFIDENCE_THRESHOLD` | 0.60 | Higher = fewer reviews, more no-matches |
| Score Weights (Filter/Fuzzy/Embedding) | 0.4/0.3/0.3 | Adjust based on data quality |

---

## Performance Metrics

### 📈 **Benchmark Results** (152 test cases)

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Success Rate** | 100.0% | No system failures |
| **Top-3 Accuracy** | 94.7% (144/152) | Correct AMIS in top 3 |
| **Top-1 Accuracy** | 63.2% (96/152) | Exact match in position 1 |
| **Average Processing Time** | 1,618ms | Including LLM calls |
| **LLM Coverage** | 68.9% (314/456) | LLM scores available |

### 🚗 **Performance by Vehicle Type**

| Vehicle Type | Top-3 Accuracy | Top-1 Accuracy | Count |
|--------------|----------------|----------------|-------|
| **DOLLY** | 100.0% (38/38) | 63.2% (24/38) | 38 |
| **TRACTO** | 97.2% (35/36) | 69.4% (25/36) | 36 |
| **TANQUE** | 91.0% (71/78) | 60.3% (47/78) | 78 |

### ⏱️ **Processing Time Breakdown**
- **Preprocessing**: ~50ms
- **Field Extraction**: ~200ms  
- **Candidate Filtering**: ~100ms
- **Fuzzy + Embedding**: ~300ms
- **LLM Finalizer**: ~800ms (when used)
- **Decision Engine**: ~10ms

---

## Debugging & Troubleshooting

### 🔍 **Debug Logging**

Enable detailed logging to diagnose issues:

```python
# Set debug level in field extraction
[DEBUG] ===== MARCA EXTRACTION =====
[DEBUG] Description: 'tracto tr freightliner cascadia'
[DEBUG] Candidates (56 total): ['freightliner', 'international', ...]
[DEBUG] Stage 1: Direct substring matching
[DEBUG] ✅ DIRECT MATCH FOUND: 'freightliner' found in description
```

### 🐛 **Common Issues & Solutions**

#### **Issue: "tanque" not being extracted**
**Cause**: Over-aggressive submarca filtering by uncertain marca  
**Solution**: Fixed - now only filters when marca confidence = 1.0  
**Code**: `field_extractor.py` line 67

#### **Issue: Low Top-1 accuracy** 
**Cause**: Score mixing weights may favor recall over precision  
**Solution**: Increase filter score weight from 0.4 to 0.5  
**Impact**: May reduce Top-3 accuracy but improve Top-1

#### **Issue: LLM timeout errors**
**Cause**: OpenAI API rate limits or network issues  
**Solution**: Implement exponential backoff and fallback scoring  
**Fallback**: Use mixed scores without LLM when API unavailable

### 📊 **Monitoring Commands**

```bash
# Run performance benchmark
python tools/test_codifier_performance.py

# Test specific vehicle  
python -c "
from services.vehicle_codifier.src.vehicle_codifier import VehicleCodeifier
codifier = VehicleCodeifier()
result = codifier.match_vehicle({'modelo': 2022, 'description': 'TANQUE TANQUE ATRO 31,500 LTS'})
print(result.candidates[:3])
"

# Check embedding model status
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('intfloat/multilingual-e5-large')  
print('Model loaded successfully')
"
```

---

## Code References

### 📁 **File Structure**
```
services/vehicle-codifier/src/vehicle_codifier/
├── core/
│   └── service.py              # Main VehicleCodeifier class
├── pipeline/
│   ├── preprocessor.py         # Input cleaning & normalization
│   ├── field_extractor.py      # Extract marca/submarca/tipveh  
│   ├── filtering.py            # Candidate filtering logic
│   ├── fuzzy_matching.py       # String similarity scoring
│   ├── embedding_scoring.py    # Semantic similarity scoring
│   ├── llm_finalizer.py        # AI-powered reranking
│   └── decision_engine.py      # Final decision logic
├── search/
│   ├── candidate_filter.py     # AMIS catalog filtering
│   └── candidate_matcher.py    # Candidate matching logic
└── models.py                   # Data models & schemas
```

### 🔑 **Key Classes & Methods**

```python
# Main entry point
class VehicleCodeifier:
    def match_vehicle(self, vehicle_input: VehicleInput) -> MatchResult

# Field extraction with confidence scoring
class FieldExtractor:
    def extract_fields_with_confidence(self, description: str, year: int) -> ExtractedFieldsWithConfidence
    def _extract_field_with_confidence(self, description: str, candidates: Set[str]) -> FieldConfidence

# High-performance candidate filtering
def filter_candidates_with_high_confidence(
    extracted_fields: ExtractedFieldsWithConfidence,
    year: int,
    engine: Engine,
    settings: Settings
) -> Tuple[List[CandidateMatch], List[str]]

# LLM-powered final reranking
def finalize_candidates_with_llm(
    candidates: List[CandidateMatch],
    description: str,
    extracted_fields: ExtractedFields,
    year: int,
    openai_client: OpenAI,
    model: str
) -> Tuple[List[Dict], Optional[str]]
```

---

## 🔄 **Workflow Summary**

The Vehicle Codifier processes vehicle information through a sophisticated 6-step pipeline:

1. **Preprocess** → Clean and normalize input data
2. **Extract** → Identify marca, submarca, tipveh with confidence scores  
3. **Filter** → Reduce AMIS catalog search space using extracted fields
4. **Score** → Apply fuzzy matching and semantic embedding similarity
5. **Mix** → Combine scores using weighted formula (40%/30%/30%)
6. **Decide** → LLM reranking and final decision (auto_accept/needs_review/no_match)

This multi-layered approach achieves **94.7% Top-3 accuracy** while maintaining **100% system reliability** across diverse vehicle types and descriptions.

---

*Last Updated: September 2025*  
*Version: 2.0*  
*For technical support, see: [Troubleshooting Guide](#debugging--troubleshooting)*
