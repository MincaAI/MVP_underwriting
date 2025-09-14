# Document Processor Service Documentation

The Document Processor Service is a unified Excel/CSV processing service that handles the complete document lifecycle from extraction through export. It consolidates document processing functionality into a single, efficient service with professional Excel output capabilities.

## Service Overview

### **Purpose**
- Process Excel/CSV files with intelligent header mapping
- Transform data using configurable broker profiles  
- Generate professional Gcotiza-ready Excel exports
- Provide real-time processing status and progress tracking

### **Technology Stack**
- **Framework**: FastAPI (Python 3.11+) with async processing
- **Excel Processing**: openpyxl with professional formatting and styling
- **Data Processing**: pandas for data manipulation and validation
- **Background Tasks**: FastAPI BackgroundTasks for async operations
- **Storage**: MinIO/S3 for file storage with presigned URLs
- **Validation**: Comprehensive data validation with business rules

### **Port**: 8001 (configurable)

## Architecture Overview

### Processing Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upload    │ ─> │   Extract   │ ─> │ Transform   │ ─> │   Export    │
│             │    │             │    │             │    │             │
│ • File I/O  │    │ • Parse     │    │ • Validate  │    │ • Format    │
│ • Metadata  │    │ • Headers   │    │ • Profiles  │    │ • Upload    │
│ • Storage   │    │ • Rows      │    │ • Rules     │    │ • URLs      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Service Components

#### **Extractor Module**
- **Intelligent Header Detection**: 80+ Spanish/English synonyms
- **Format Support**: Excel (.xlsx, .xls) and CSV files
- **Data Validation**: Comprehensive VIN, year, and business rule validation
- **Error Handling**: Detailed error reporting with row-level diagnostics

#### **Transformer Module**
- **Profile Engine**: YAML-based broker-specific transformation rules
- **Field Mapping**: Configurable source-to-canonical field mapping
- **Data Normalization**: Text cleaning, standardization, and validation
- **Business Logic**: Complex calculations and derived field generation

#### **Exporter Module**
- **Professional Formatting**: Gcotiza-compliant 46-column Excel output
- **Advanced Styling**: Headers, borders, fonts, and conditional formatting
- **Template System**: Configurable export templates (gcotiza_v1.yaml, etc.)
- **S3 Integration**: Automatic upload with metadata and checksums

## Key Features

### 📁 **Intelligent File Processing**
- **Smart Header Detection**: Automatic mapping of 80+ column variations
- **Multi-format Support**: Excel (.xlsx, .xls) and CSV file processing  
- **Encoding Detection**: Automatic character encoding detection
- **Large File Handling**: Efficient processing of files with thousands of rows

### 🔄 **Configurable Transformation**
- **Broker Profiles**: YAML-based transformation rules per broker
- **Field Mapping**: Flexible source-to-target field mapping
- **Data Validation**: Comprehensive business rule validation
- **Error Recovery**: Intelligent error handling with detailed reporting

### 📤 **Professional Export**
- **Gcotiza Format**: Industry-standard 46-column Excel format
- **Advanced Styling**: Professional formatting with colors and borders
- **Template System**: Multiple export templates for different use cases
- **Metadata Preservation**: Comprehensive export metadata and checksums

### ⚡ **Async Processing**
- **Background Tasks**: Non-blocking processing with real-time status
- **Progress Tracking**: Detailed progress reporting with metrics
- **Status Monitoring**: Real-time processing status via `/status/{run_id}`
- **Error Handling**: Comprehensive error capture and reporting

## API Endpoints

### Complete Processing Pipeline

#### `POST /process` - Full Document Processing
Complete end-to-end processing from upload to export.

**Request:**
```bash
curl -X POST "http://localhost:8001/process" \
  -F "file=@broker_fleet.xlsx" \
  -F "case_id=CASE_2024_001" \
  -F "profile=lucky_gas.yaml" \
  -F "export_template=gcotiza_v1.yaml"
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "case_id": "CASE_2024_001", 
  "status": "processing",
  "message": "Document processing started successfully"
}
```

### Individual Processing Steps

#### `POST /extract` - Extract Data from File
Parse and extract data from uploaded Excel/CSV files.

**Request Parameters:**
- `file`: Excel or CSV file (multipart/form-data)
- `case_id`: Case identifier
- `profile`: Broker profile for header mapping (optional)

**Response:**
```json
{
  "run_id": "uuid-v4",
  "extracted_rows": 150,
  "headers_detected": {
    "marca": "brand",
    "submarca": "model", 
    "año": "year",
    "descripcion": "description"
  },
  "validation_summary": {
    "valid_rows": 148,
    "invalid_rows": 2,
    "warnings": 5
  }
}
```

#### `POST /transform/{run_id}` - Transform Extracted Data
Apply broker profile transformations to extracted data.

**Query Parameters:**
- `profile`: Broker profile name (default: generic.yaml)

**Response:**
```json
{
  "run_id": "uuid-v4",
  "status": "SUCCESS",
  "metrics": {
    "rows_processed": 150,
    "transformations_applied": 12,
    "validation_errors": {},
    "processing_time_ms": 850
  },
  "preview": [
    {
      "row_idx": 0,
      "transformed": {
        "brand": "nissan",
        "model": "sentra", 
        "year": 2020,
        "body": "sedan",
        "use": "particular",
        "description": "nissan sentra 2020 sedan particular"
      },
      "errors": {},
      "warnings": {}
    }
  ]
}
```

#### `POST /export/{run_id}` - Export to Excel
Generate professional Excel export from processed data.

**Query Parameters:**
- `template`: Export template name (default: gcotiza_v1.yaml)

**Response:**
```json
{
  "export_id": "uuid-v4",
  "file_url": "s3://exports/gcotiza/uuid_20240915_143022.xlsx",
  "download_url": "https://presigned-url...",
  "checksum": "sha256-hash",
  "metadata": {
    "rows": 150,
    "columns": 46,
    "file_size_bytes": 1245760,
    "created_at": "2024-09-15T14:30:22.123456Z"
  }
}
```

### Status and Monitoring

#### `GET /status/{run_id}` - Real-time Processing Status
Get current processing status with detailed progress information.

**Response:**
```json
{
  "run_id": "uuid-v4",
  "case_id": "CASE_2024_001",
  "status": "transforming",
  "progress": 75.5,
  "current_step": "Applying broker profile transformations",
  "steps_completed": ["extract", "validate"],
  "steps_remaining": ["transform", "export"],
  "metrics": {
    "total_rows": 150,
    "processed_rows": 113,
    "error_rows": 2,
    "warning_rows": 5
  },
  "estimated_completion": "2024-09-15T14:32:15Z",
  "started_at": "2024-09-15T14:30:00Z"
}
```

#### `GET /health` - Service Health Check
Check service health and configuration.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-09-15T14:30:22.123456",
  "version": "1.0.0",
  "services": {
    "s3_storage": "connected",
    "database": "connected", 
    "background_tasks": "running"
  },
  "configuration": {
    "supported_formats": [".xlsx", ".xls", ".csv"],
    "max_file_size": "50MB",
    "max_rows": 10000
  }
}
```

## Configuration

### Environment Variables

```bash
# S3/MinIO Storage
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minio
AWS_SECRET_ACCESS_KEY=minio12345
S3_BUCKET_RAW=raw
S3_BUCKET_EXPORTS=exports

# Database Connection
DATABASE_URL=postgresql+psycopg://minca:minca@db:5432/minca

# Processing Configuration
MAX_FILE_SIZE_MB=50
MAX_ROWS_PER_FILE=10000
DEFAULT_PROFILE=generic.yaml
DEFAULT_EXPORT_TEMPLATE=gcotiza_v1.yaml

# Service Configuration
DEBUG=true
LOG_LEVEL=INFO
```

### Broker Profiles

Broker profiles are YAML files that define transformation rules:

```yaml
# configs/broker-profiles/lucky_gas.yaml
name: "Lucky Gas Fleet Profile"
description: "Transformation profile for Lucky Gas broker files"

# Field mappings
field_mappings:
  "marca": "brand"
  "submarca": "model"
  "año": "year"
  "carrocería": "body"
  "uso": "use"
  "descripción": "description"
  "placa": "license_plate"
  "valor asegurado": "insured_value"
  "prima": "premium"

# Data transformations
transformations:
  brand:
    - type: "normalize"
      rules: ["uppercase", "trim"]
  year:
    - type: "convert"
      target_type: "integer"
    - type: "validate"
      min_value: 1990
      max_value: 2025

# Business rules
validation_rules:
  required_fields: ["brand", "model", "year", "description"]
  vin_validation: true
  year_range: [1990, 2025]
```

### Export Templates

Export templates define the output format:

```yaml
# configs/gcotiza-templates/gcotiza_v1.yaml
name: "Gcotiza Export Template v1"
description: "Standard Gcotiza 46-column Excel format"

# Column definitions (A-AT = 46 columns)
columns:
  A: "CLAVE VEHICULO"      # CVEGS code
  B: "MARCA"               # Vehicle brand
  C: "MODELO"              # Vehicle model
  D: "AÑO"                 # Vehicle year
  E: "CARROCERIA"          # Body type
  F: "USO"                 # Vehicle use
  # ... (46 total columns)

# Styling configuration
styling:
  header:
    background_color: "366092"
    font_color: "FFFFFF"
    font_bold: true
  data:
    font_name: "Calibri"
    font_size: 11
    border_style: "thin"
```

## Data Processing Details

### Header Detection

The service uses intelligent header detection with 80+ synonyms:

```python
HEADER_SYNONYMS = {
    "brand": [
        "marca", "brand", "make", "fabricante", "constructor",
        "marca vehiculo", "marca_vehiculo", "marcavehiculo"
    ],
    "model": [
        "modelo", "model", "submarca", "sub_marca", "sub-marca",
        "linea", "línea", "version", "versión"
    ],
    "year": [
        "año", "ano", "year", "model_year", "año_modelo",
        "año modelo", "año_vehiculo", "fecha_fabricacion"
    ],
    # ... (80+ total mappings)
}
```

### Data Validation

Comprehensive validation rules are applied:

```python
VALIDATION_RULES = {
    "vin": {
        "pattern": r"^[A-HJ-NPR-Z0-9]{17}$",
        "required": False
    },
    "year": {
        "type": "integer",
        "min_value": 1990,
        "max_value": 2025,
        "required": True
    },
    "brand": {
        "type": "string",
        "min_length": 2,
        "max_length": 50,
        "required": True
    }
}
```

### Excel Export Format

The Gcotiza export generates a professional 46-column Excel file:

- **Columns A-F**: Vehicle identification (CVEGS, brand, model, year, body, use)
- **Columns G-O**: Additional vehicle details and descriptions
- **Columns P-AT**: Coverage information (deductibles, limits, terms, etc.)

## Performance Characteristics

### Benchmarks
- **File Processing**: ~100 rows/second for typical Excel files
- **Header Detection**: ~50ms average for files with up to 20 columns
- **Data Validation**: ~10ms per row with comprehensive rule checking
- **Excel Export**: ~200 rows/second with professional formatting

### File Size Limits
- **Maximum File Size**: 50MB (configurable)
- **Maximum Rows**: 10,000 rows per file (configurable)
- **Supported Formats**: .xlsx, .xls, .csv
- **Memory Usage**: ~2MB per 1000 rows during processing

## Integration

### With Main API Service
```python
# Main API orchestrates document processing
response = requests.post(
    "http://document-processor:8001/process",
    files={"file": file_content},
    data={"case_id": case_id, "profile": profile}
)
```

### With Database Layer
```python
# Uses shared database models
from app.db.models import Run, Row, Export
```

### With Storage Service
```python
# Integrates with MinIO/S3 for file storage
from app.storage.client import upload_file, get_presigned_url
```

## Development

### Running the Service

**With Docker:**
```bash
docker-compose up document-processor
```

**Locally:**
```bash
cd services/document-processor
poetry install
poetry run uvicorn document_processor.main:app --reload --port 8001
```

### Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# End-to-end tests
pytest tests/e2e/ -v

# Test with sample files
curl -X POST "http://localhost:8001/process" \
  -F "file=@data/samples/lucky_gas_fleet.xlsx" \
  -F "case_id=TEST_CASE" \
  -F "profile=lucky_gas.yaml"
```

### Adding New Broker Profiles

1. **Create Profile YAML**: Add new profile in `configs/broker-profiles/`
2. **Test Mapping**: Validate field mappings with sample data
3. **Update Documentation**: Document any special transformation rules
4. **Add Tests**: Create test cases for the new profile

### Adding Export Templates

1. **Define Template**: Create YAML template in `configs/gcotiza-templates/`
2. **Configure Columns**: Define all output columns and mappings
3. **Style Configuration**: Set up Excel formatting and styling
4. **Test Export**: Validate output format and styling

## Troubleshooting

### Common Issues

**File Upload Errors:**
- Check file size limits (default 50MB)
- Verify supported file formats (.xlsx, .xls, .csv)
- Ensure proper multipart/form-data encoding

**Header Detection Issues:**
- Review header synonym mappings
- Check for non-standard column names
- Consider adding custom synonyms to profile

**Transformation Errors:**
- Validate broker profile YAML syntax
- Check field mapping configurations
- Review data type conversion rules

**Export Formatting Issues:**
- Verify export template configuration
- Check column count (Gcotiza requires 46 columns)
- Review Excel styling and formatting rules

**Storage Issues:**
- Verify S3/MinIO connection settings
- Check bucket permissions and accessibility
- Monitor storage space and quotas

### Debug Mode

```bash
# Enable detailed logging
DEBUG=true
LOG_LEVEL=DEBUG

# Enable request/response logging
TRACE_REQUESTS=true

# Enable Excel processing debug
EXCEL_DEBUG=true
```

### Performance Monitoring

```bash
# Monitor processing times
GET /status/{run_id}

# Check service health
GET /health

# Monitor file processing metrics
# Review logs for processing times and bottlenecks
```

## Future Enhancements

- **Parallel Processing**: Multi-threaded processing for large files
- **Advanced Validation**: ML-powered data quality validation
- **Template Editor**: Web-based template configuration interface
- **Streaming Processing**: Support for very large files via streaming
- **Custom Formats**: Support for additional export formats beyond Excel
- **Data Quality Metrics**: Advanced data quality scoring and reporting

---

The Document Processor Service provides robust, professional-grade document processing capabilities that handle the complete lifecycle from upload to export, with comprehensive error handling and real-time monitoring.