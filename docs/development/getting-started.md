# Getting Started Guide

This guide provides step-by-step instructions for setting up the Minca AI Insurance MVP Underwriting Platform for development and testing.

## Prerequisites

### **Required Software**
- **Python 3.11+**: For backend services
- **Poetry**: Python dependency management
- **Docker & Docker Compose**: For containerized development
- **PostgreSQL 15+**: Database with pgvector extension
- **MinIO**: S3-compatible object storage
- **Git**: Version control

### **Required Data**
- **Vehicle Catalogue Excel** (e.g., CATVER_ENVIOS.xlsx)
- **Sample Broker Files**: Excel/CSV files for testing transformations

## Setup Instructions

### **1. Install Poetry**
```bash
# Install Poetry using official installer
curl -sSL https://install.python-poetry.org | python3 -
```

### **2. Start Development Environment**
```bash
# Start PostgreSQL + MinIO + pgAdmin
make dev

# This starts:
# - PostgreSQL with pgvector extension (port 5432)
# - MinIO object storage (port 9000, console 9001)  
# - pgAdmin web interface (port 8080)
```

### **3. Initialize Database**
```bash
cd packages/db
poetry install
poetry run alembic upgrade head
```

### **4. Load Catalog Data (S3 + Postgres Versioning)**
```bash
# Load catalog with versioning
python tools/catalog_load.py \
  --version "dev-v1.0" \
  --file "data/amis-catalogue/sample.xlsx" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca"

# Generate embeddings
python tools/catalog_embed.py \
  --version "dev-v1.0" \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  --model-id "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Activate catalog version
python tools/catalog_activate.py \
  --db "postgresql+psycopg://minca:minca@localhost:5432/minca" \
  activate --version "dev-v1.0"

# Verify counts (optional)
python - <<'PY'
import sys
sys.path.insert(0, 'packages/db/src')
from sqlalchemy import text
from app.db.session import engine
with engine.begin() as cx:
    for t in ['sample_raw','catver_envios_raw']:
        try:
            c = cx.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
            print(t, c)
        except Exception:
            pass
PY
```

### **5. Start API Service**
```bash
cd services/api
poetry install
./run_local.sh

# API available at: http://localhost:8000
# Documentation: http://localhost:8000/docs
```

**Alternative startup methods:**
```bash
# Method 1: Using the shell script (recommended)
./run_local.sh

# Method 2: Using the Python launcher
python run_api.py

# Method 3: Direct uvicorn command
poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Package Dependencies:**
The API service now includes the following workspace packages:
- `db`: Database models and session management
- `storage`: S3/MinIO storage utilities
- `schemas`: Pydantic schemas and data models
- `mincaai-mq`: Message queue utilities for local and SQS backends

All dependencies are automatically installed when running `poetry install`.

## Quick Testing

### **1. Test API Health**
```bash
curl http://localhost:8000/health
# Should return: {"ok": true, "db": "...", "s3": "..."}
```

### **2. Test Complete Workflow**
```bash
# 1. Transform broker data (requires S3 file)
curl -X POST "http://localhost:8000/transform?case_id=test&s3_uri=s3://bucket/file.xlsx"

# 2. Preview transformed data  
curl "http://localhost:8000/transform/preview?run_id=<uuid>&limit=5"

# 3. Run vehicle codification
curl -X POST "http://localhost:8000/codify/batch?run_id=<uuid>"

# 4. Export to Gcotiza format
curl -X POST "http://localhost:8000/export?run_id=<uuid>"

# 5. Get download link
curl "http://localhost:8000/export/download?run_id=<uuid>"
```

### **3. Test Utilities**
```bash
# Evaluate codifier accuracy (optional)
./tools/eval_codifier.py --file data/samples/labeled_100.csv
```

## Complete Platform Setup

### **1. Database Service Setup**
```bash
cd services/database-service

# Configure environment
cp .env.example .env
# Edit .env with database URL:
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/insurance_db

# Install dependencies with Poetry
poetry install

# Start PostgreSQL (if not using Docker)
# Or use Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15

# Run migrations
alembic upgrade head

# Test database connection
python -c "
import asyncio
from app.config.database import check_db_connection
print('Database connected:', asyncio.run(check_db_connection()))
"
```

### **2. Smart Intake Service Setup**
```bash
cd services/smart-intake-service

# Configure environment
cp .env.example .env
# Edit .env with required settings:
# AZURE_TENANT_ID=your_tenant_id (optional for testing)
# AZURE_CLIENT_ID=your_client_id (optional for testing)
# AZURE_CLIENT_SECRET=your_client_secret (optional for testing)
# OPENAI_API_KEY=your_openai_api_key
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/insurance_db

# Install dependencies with Poetry
poetry install

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Start Celery worker (in separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Start FastAPI service
python -m uvicorn app.main:app --reload --port 8002

# Service available at: http://localhost:8002
```

### **3. Smart Intake Service Setup**
```bash
cd services/smart-intake-service

# Install dependencies with Poetry
poetry install

# Activate Poetry shell
poetry shell

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Configure environment
export OPENAI_API_KEY=your_openai_api_key_here
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/insurance_db
export REDIS_URL=redis://localhost:6379

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Start FastAPI service
python -m uvicorn app.main:app --reload --port 8002

# Service available at: http://localhost:8002
```

### **4. Frontend Application Setup**
```bash
cd ui

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with API URLs:
# NEXT_PUBLIC_SMART_INTAKE_URL=http://localhost:8002
# NEXT_PUBLIC_VEHICLE_MATCHER_URL=http://localhost:8000
# NEXT_PUBLIC_DATABASE_URL=http://localhost:8001

# Start development server
npm run dev

# Application available at: http://localhost:3000
```

### **5. Claveteador Workflow Components**

The frontend now includes a complete **Claveteador workflow** with the following components:

#### **Component Structure**
```
ui/src/components/
├── NewDashboard.tsx          # Main workflow container
├── SmartIntakeResults.tsx    # Step 1: Smart intake dashboard
├── Claveteador.tsx          # Step 2: Data preprocessing
├── VehicleMatching.tsx      # Step 3: AMIS vehicle matching
├── ExcelExport.tsx          # Step 4: Final export
└── QuickEmailInput.tsx      # Floating email input
```

#### **Testing the Claveteador Workflow**
```bash
# 1. Start the frontend
npm run dev

# 2. Open http://localhost:3000
# 3. Test the complete workflow:

# Step 1: Smart Intake Dashboard
# - View processed email results
# - Click "Process" on complete cases
# - Use filters to find specific cases

# Step 2: Claveteador (Data Preprocessing)
# - Review email content and attachments
# - Complete company information form
# - Configure coverage requirements
# - Review claims history
# - Click "🔍 Claveteador" to proceed

# Step 3: Vehicle Matching
# - Review codification summary statistics
# - Edit vehicle data inline
# - Filter by AMIS status
# - Click "✅ VALIDATE CLAVE AMIS"

# Step 4: Excel Export
# - Review final vehicle data
# - Adjust agent discount percentage
# - Click "📄 Download Excel Cotizador"
```

#### **Component Development**
```bash
# Hot reload is enabled for all components
# Make changes to any .tsx file and see immediate updates

# Key files for Claveteador workflow:
# - NewDashboard.tsx: Main state management and navigation
# - Each step component: Individual workflow steps
# - Navigation between steps is handled by state changes

# Test component isolation:
cd ui
npm run storybook  # If Storybook is configured
```

## Service-by-Service Setup

### **Vehicle CVEGS Matcher Service**

#### **Local Development**
```bash
cd services/vehicle-matcher

# Install dependencies with Poetry (Poetry manages virtual environment)
poetry install

# Activate Poetry shell
poetry shell

# Configure environment
export OPENAI_API_KEY=your_openai_api_key_here
export DEBUG=true

# Add dataset
cp your_cvegs_dataset.xlsx data/cvegs_dataset.xlsx

# Start service
python -m uvicorn app.main:app --reload --port 8000
```

#### **Docker Development**
```bash
cd services/vehicle-matcher

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start with Docker Compose
docker-compose up --build

# View logs
docker-compose logs -f vehicle-matcher
```

### **Database Service**

#### **Local Development**
```bash
cd services/database-service

# Install dependencies with Poetry
poetry install

# Activate Poetry shell
poetry shell

# Start PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=insurance_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  postgres:15

# Configure database URL
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/insurance_db

# Run migrations
alembic upgrade head

# Test repository functionality
python -c "
import asyncio
from app.repositories.case_repository import CaseRepository
from app.config.database import AsyncSessionLocal

async def test():
    async with AsyncSessionLocal() as db:
        repo = CaseRepository(db)
        cot = await repo.generate_cot_number()
        print(f'Generated COT: {cot}')

asyncio.run(test())
"
```

### **Smart Intake Service**

#### **Local Development**
```bash
cd services/smart-intake-service

# Install dependencies with Poetry
poetry install

# Activate Poetry shell
poetry shell

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Configure environment
export OPENAI_API_KEY=your_openai_api_key_here
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/insurance_db
export REDIS_URL=redis://localhost:6379

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Start FastAPI service
python -m uvicorn app.main:app --reload --port 8002
```

### **Frontend Application**

#### **Local Development**
```bash
cd frontend/smart-intake-ui

# Install dependencies
npm install

# Configure environment
cat > .env.local << EOF
NEXT_PUBLIC_SMART_INTAKE_URL=http://localhost:8002
NEXT_PUBLIC_VEHICLE_MATCHER_URL=http://localhost:8000
NEXT_PUBLIC_DATABASE_URL=http://localhost:8001
EOF

# Start development server
npm run dev

# Build for production
npm run build
npm start
```

## Complete Stack with Docker

### **Docker Compose for All Services**
```yaml
# docker-compose.yml (root level)
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: insurance_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  vehicle-matcher:
    build: ./services/vehicle-matcher
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./services/vehicle-matcher/data:/app/data
    depends_on:
      - redis

  database-service:
    build: ./services/database-service
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/insurance_db
    depends_on:
      - postgres

  smart-intake:
    build: ./services/smart-intake-service
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/insurance_db
      - REDIS_URL=redis://redis:6379
      - VEHICLE_MATCHER_URL=http://vehicle-matcher:8000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
      - vehicle-matcher

  frontend:
    build: ./frontend/smart-intake-ui
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_SMART_INTAKE_URL=http://localhost:8002
      - NEXT_PUBLIC_VEHICLE_MATCHER_URL=http://localhost:8000
      - NEXT_PUBLIC_DATABASE_URL=http://localhost:8001
    depends_on:
      - smart-intake

volumes:
  postgres_data:
```

### **Start Complete Stack**
```bash
# Create environment file
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env

# Start all services
docker-compose up --build

# Services will be available at:
# - Frontend: http://localhost:3000
# - Smart Intake: http://localhost:8002
# - Vehicle Matcher: http://localhost:8000
# - Database: localhost:5432
```

### **Testing the New Broker Profile System**

#### **1. Test Manual Email Entry**
```bash
# 1. Open the frontend
open http://localhost:3000

# 2. Navigate to "📧 Manual Email Entry" tab
# 3. Enter test email data:
#    - From: broker@luckygas.com.mx
#    - Subject: Fleet Insurance Request - Test Company
#    - Content: Please find attached our vehicle fleet for insurance
#    - Upload a test Excel file with vehicle data

# 4. Click "🚀 Process Email Data"
# 5. Monitor real-time processing status
```

#### **2. Test Broker Profile Management**
```bash
# 1. Navigate to "🏢 Broker Profiles" tab
# 2. View existing profiles and usage statistics
# 3. Click "🤖 Auto-Generate" to test profile creation wizard
# 4. Walk through the 3-step wizard:
#    - Step 1: Review AI detection results
#    - Step 2: Edit field mappings
#    - Step 3: Validate and save profile
```

#### **3. Test Profile Auto-Detection**
```bash
# Test broker detection API directly
curl "http://localhost:8002/broker-profiles/detect?email=broker@luckygas.com.mx"

# Should return existing profile or suggest new one
```

## Testing the Complete Workflow

### **1. Test Vehicle Matching**
```bash
# Test single vehicle
curl -X POST "http://localhost:8000/match/single" \
  -H "Content-Type: application/json" \
  -d '{"description": "TOYOTA YARIS SOL L 2020"}'

# Test batch matching
curl -X POST "http://localhost:8000/match/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicles": [
      {"description": "TOYOTA YARIS SOL L 2020"},
      {"description": "MITSUBISHI L200 DIESEL 4X4 DC 2018"}
    ]
  }'
```

### **2. Test Database Operations**
```bash
# Check database health
curl http://localhost:8001/health

# Get dashboard statistics
curl http://localhost:8001/stats/dashboard
```

### **3. Test Smart Intake**
```bash
# Check smart intake health
curl http://localhost:8002/health

# Check Celery worker status
curl http://localhost:8002/tasks/stats
```

### **4. Test Frontend**
```bash
# Open dashboard
open http://localhost:3000

# Check API integration
curl http://localhost:3000/api/health
```

## Development Workflow

### **Working with Broker Profiles**

#### **Creating Custom Broker Profiles**
```bash
# 1. Create new YAML profile
mkdir -p configs/broker-profiles
cat > configs/broker-profiles/custom_broker.yaml << EOF
name: "Custom Broker Profile"
description: "Profile for custom broker format"

detect:
  required_headers: ["Vehicle_Make", "Vehicle_Model", "Year"]

mapping:
  columns:
    "Vehicle_Make": "brand"
    "Vehicle_Model": "model"
    "Year": "year"
    "Description": "description"
  
  normalize:
    brand: "upper, strip, deburr"
    model: "strip, deburr"

compute:
  add_columns:
    description: "{brand} {model} {year}"

validate:
  required: ["brand", "model", "year"]
  ranges:
    year: {min: 1990, max: 2025}
EOF

# 2. Test the profile
curl -X POST "http://localhost:8002/broker-profiles" \
  -H "Content-Type: application/json" \
  -d @configs/broker-profiles/custom_broker.yaml
```

#### **Testing Profile Generation**
```bash
# 1. Use the frontend wizard for interactive profile creation
# 2. Or test the API directly for programmatic generation

# Mock LLM response for field detection
curl -X POST "http://localhost:8002/detect-fields" \
  -F "file=@sample_broker_file.xlsx" \
  -F "email_domain=newbroker.com"
```

### **Making Changes**

#### **Backend Services**
```bash
# 1. Make changes to Python code
# 2. Run tests
cd services/vehicle-matcher
python -m pytest tests/ -v

# 3. Check linting
black app/ tests/
flake8 app/ tests/

# 4. Restart service
docker-compose restart vehicle-matcher
```

#### **Frontend Application**
```bash
# 1. Make changes to TypeScript/React code
# 2. Type check
npm run type-check

# 3. Run tests
npm test

# 4. Lint code
npm run lint

# Hot reload is automatic in development
```

#### **Database Changes**
```bash
# 1. Modify SQLAlchemy models
# 2. Generate migration
cd services/database-service
alembic revision --autogenerate -m "Description of changes"

# 3. Review migration
# 4. Apply migration
alembic upgrade head
```

## Troubleshooting

### **Common Issues**

#### **OpenAI API Errors**
```bash
# Check API key
echo $OPENAI_API_KEY

# Test API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL status
docker ps | grep postgres

# Test connection
psql -h localhost -U postgres -d insurance_db -c "SELECT 1;"

# Check database URL format
echo $DATABASE_URL
```

#### **Service Communication Issues**
```bash
# Check service health
curl http://localhost:8000/health  # Vehicle Matcher
curl http://localhost:8001/health  # Database Service
curl http://localhost:8002/health  # Smart Intake

# Check Docker network
docker network ls
docker network inspect minca-ai-insurance_default
```

#### **Frontend Issues**
```bash
# Check Node.js version
node --version  # Should be 18+

# Clear Next.js cache
rm -rf .next
npm run build

# Check API connectivity
curl http://localhost:3000/api/vehicle-matcher/health
```

### **Debug Mode**
```bash
# Enable debug logging for all services
export DEBUG=true
export LOG_LEVEL=DEBUG

# View service logs
docker-compose logs -f service-name

# Monitor Celery tasks
celery -A app.tasks.celery_app flower
# Open http://localhost:5555
```

## Performance Optimization

### **Development Performance**
- **Hot Reloading**: All services support hot reloading in development
- **Incremental Builds**: Docker layer caching for faster rebuilds
- **Parallel Processing**: Services can run independently
- **Resource Limits**: Configure Docker resource limits as needed

### **Production Considerations**
- **Environment Variables**: Use production-appropriate values
- **Resource Allocation**: Scale services based on load
- **Monitoring**: Enable comprehensive logging and metrics
- **Security**: Configure proper authentication and secrets management

## Next Steps

### **After Setup**
1. **Explore APIs**: Visit service documentation endpoints
2. **Test Workflows**: Try the complete email processing workflow
3. **Review Code**: Understand the codebase structure and patterns
4. **Make Changes**: Follow the development workflow for modifications

### **For Production**
1. **Azure Setup**: Configure Microsoft Graph app registration
2. **AWS Deployment**: Set up cloud infrastructure
3. **CI/CD**: Configure automated deployment pipeline
4. **Monitoring**: Set up logging and alerting

This setup provides a complete development environment for the Minca AI Insurance Platform with all services running locally and ready for development and testing.
