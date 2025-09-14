# AI Tool Development Guide

This guide is specifically designed for AI coding tools to understand the Minca AI Insurance Platform architecture, patterns, and conventions for making intelligent code modifications and additions.

## 🤖 Quick Reference for AI Tools

### **Project Structure Understanding**
```
minca-ai-insurance/
├── docs/                           # Global documentation (this folder)
├── services/                       # Microservices
│   ├── vehicle-matcher/           # Vehicle CVEGS matching service
│   └── database-service/          # Database layer and models
├── frontend/                      # Future: Next.js UI
└── infrastructure/                # Future: Terraform/AWS configs
```

### **Key Files for AI Understanding**
```python
# Core Business Logic
services/vehicle-matcher/app/services/matcher.py      # Main matching algorithm
services/vehicle-matcher/app/services/preprocessor.py # Text preprocessing
services/vehicle-matcher/app/services/llm_extractor.py # OpenAI integration

# Data Layer
services/database-service/app/models/               # SQLAlchemy models
services/database-service/app/repositories/        # Data access layer

# API Layer
services/vehicle-matcher/app/main.py               # FastAPI application
services/vehicle-matcher/app/models/vehicle.py     # Pydantic models

# Configuration
services/*/app/config/settings.py                 # Environment settings
services/*/requirements.txt                       # Dependencies
```

## 🏗️ Architecture Patterns

### **1. Microservices Pattern**
Each service is independent with its own:
- **Database models** and repositories
- **API endpoints** and validation
- **Configuration** and environment variables
- **Docker container** and deployment

```python
# Service structure pattern
service-name/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config/settings.py   # Configuration
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── utils/               # Utilities
├── requirements.txt         # Dependencies
├── Dockerfile              # Container config
└── docker-compose.yml      # Local development
```

### **2. Repository Pattern**
Data access is abstracted through repositories:

```python
# Base repository pattern
class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def create(self, **kwargs) -> ModelType:
        # Create new record
    
    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        # Get by primary key
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        # Update existing record

# Specific repository with business logic
class CaseRepository(BaseRepository[Case]):
    async def create_case_with_cot(self, **kwargs) -> Case:
        # Business logic for COT generation
    
    async def get_cases_needing_review(self) -> List[Case]:
        # Complex business queries
```

### **3. FastAPI Patterns**
All APIs follow consistent patterns:

```python
# Endpoint pattern
@app.post("/endpoint", response_model=ResponseModel, tags=["Category"])
async def endpoint_function(
    request_data: RequestModel,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info("Endpoint called", data=request_data.dict())
        
        # Business logic
        result = await service.process(request_data)
        
        logger.info("Endpoint completed", result=result)
        return result
        
    except Exception as e:
        logger.error("Endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

### **4. Async/Await Pattern**
All I/O operations are asynchronous:

```python
# Database operations
async def get_case(db: AsyncSession, case_id: str) -> Optional[Case]:
    result = await db.execute(select(Case).where(Case.id == case_id))
    return result.scalar_one_or_none()

# HTTP requests
async def call_vehicle_matcher(vehicles: List[VehicleInput]) -> BatchMatchResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        return BatchMatchResponse(**response.json())

# File operations
async def save_file(content: bytes, path: str):
    async with aiofiles.open(path, 'wb') as f:
        await f.write(content)
```

## 🔧 Code Conventions

### **1. Type Hints**
All functions use comprehensive type hints:

```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

async def process_vehicles(
    vehicles: List[VehicleInput],
    insurer_id: str = "default"
) -> BatchMatchResponse:
    """Process multiple vehicles with type safety."""
    pass
```

### **2. Pydantic Models**
Data validation and serialization:

```python
class VehicleInput(BaseModel):
    description: str = Field(..., description="Vehicle description")
    year: Optional[int] = Field(None, ge=1900, le=2030)
    insurer_id: str = Field("default", description="Insurer ID")
    
    @validator('description')
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()
```

### **3. Error Handling**
Comprehensive error handling with logging:

```python
try:
    result = await process_data(input_data)
    logger.info("Processing completed", result=result)
    return result
except ValidationError as e:
    logger.error("Validation failed", error=str(e))
    raise HTTPException(status_code=400, detail=str(e))
except ExternalAPIError as e:
    logger.error("External API failed", error=str(e))
    raise HTTPException(status_code=502, detail="External service unavailable")
except Exception as e:
    logger.error("Unexpected error", error=str(e), exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

### **4. Structured Logging**
Consistent logging across all services:

```python
import structlog

logger = structlog.get_logger()

# Log with context
logger.info("Vehicle matched", 
           vehicle_id=vehicle.id,
           cvegs_code=result.cvegs_code,
           confidence=result.confidence_score,
           processing_time_ms=processing_time)

# Log errors with details
logger.error("Matching failed",
            vehicle_description=description,
            error=str(e),
            request_id=request_id)
```

## 🔄 Common Development Tasks

### **Adding New API Endpoints**

1. **Define Pydantic Models**:
```python
# In app/models/
class NewRequestModel(BaseModel):
    field1: str
    field2: Optional[int] = None

class NewResponseModel(BaseModel):
    result: str
    metadata: Dict[str, Any]
```

2. **Add Business Logic**:
```python
# In app/services/
class NewService:
    async def process_request(self, request: NewRequestModel) -> NewResponseModel:
        # Implementation
        pass
```

3. **Create Endpoint**:
```python
# In app/main.py
@app.post("/new-endpoint", response_model=NewResponseModel, tags=["Category"])
async def new_endpoint(
    request_data: NewRequestModel,
    request: Request
):
    service = NewService()
    return await service.process_request(request_data)
```

4. **Add Tests**:
```python
# In tests/
@pytest.mark.asyncio
async def test_new_endpoint():
    # Test implementation
    pass
```

### **Adding Database Models**

1. **Create SQLAlchemy Model**:
```python
# In app/models/
class NewModel(Base):
    __tablename__ = "new_table"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

2. **Create Repository**:
```python
# In app/repositories/
class NewModelRepository(BaseRepository[NewModel]):
    async def get_by_name(self, name: str) -> Optional[NewModel]:
        return await self.get_by_field("name", name)
```

3. **Generate Migration**:
```bash
cd services/database-service
alembic revision --autogenerate -m "Add new_table"
alembic upgrade head
```

### **Integrating Services**

1. **HTTP Client Pattern**:
```python
class ServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def call_service(self, data: Dict) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/endpoint", json=data)
            response.raise_for_status()
            return response.json()
```

2. **Service Integration**:
```python
# In service that calls another service
vehicle_matcher_client = ServiceClient("http://vehicle-matcher:8000")
result = await vehicle_matcher_client.call_service(vehicle_data)
```

## 📊 Performance Patterns

### **Async Processing**
```python
# Parallel processing pattern
async def process_batch(items: List[Item]) -> List[Result]:
    semaphore = asyncio.Semaphore(50)  # Limit concurrency
    
    async def process_item(item: Item) -> Result:
        async with semaphore:
            return await process_single_item(item)
    
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)
```

### **Caching Pattern**
```python
# Redis caching pattern
async def get_cached_result(key: str) -> Optional[Dict]:
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    return None

async def set_cached_result(key: str, data: Dict, ttl: int = 3600):
    await redis.setex(key, ttl, json.dumps(data))
```

### **Database Optimization**
```python
# Efficient relationship loading
cases = await db.execute(
    select(Case)
    .options(selectinload(Case.vehicles))  # Eager load relationships
    .where(Case.status == "PROCESSED")
    .limit(50)
)

# Bulk operations
vehicles = [Vehicle(**data) for data in vehicle_data_list]
db.add_all(vehicles)
await db.commit()
```

## 🧪 Testing Patterns

### **Unit Tests**
```python
@pytest.mark.asyncio
async def test_vehicle_matching():
    # Arrange
    vehicle_input = VehicleInput(description="TOYOTA YARIS 2020")
    
    # Act
    result = await matcher.match_vehicle(vehicle_input)
    
    # Assert
    assert result.cvegs_code is not None
    assert result.confidence_score > 0.8
```

### **Integration Tests**
```python
@pytest.mark.asyncio
async def test_api_endpoint(client: AsyncClient):
    response = await client.post("/match/single", json={
        "description": "TOYOTA YARIS 2020",
        "insurer_id": "default"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "cvegs_code" in data
```

### **Mock External Services**
```python
@patch('app.services.llm_extractor.AsyncOpenAI')
async def test_with_mocked_openai(mock_openai):
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    
    result = await extractor.extract_attributes("TOYOTA YARIS")
    assert result.brand == "TOYOTA"
```

## 🔍 Debugging and Troubleshooting

### **Logging Analysis**
```python
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# View structured logs
docker-compose logs -f service-name | jq '.'
```

### **Common Issues and Solutions**

#### **OpenAI API Issues**
```python
# Rate limiting handling
try:
    response = await openai_client.chat.completions.create(...)
except openai.RateLimitError as e:
    logger.warning("Rate limit hit", retry_after=e.retry_after)
    await asyncio.sleep(e.retry_after)
    # Retry logic
```

#### **Database Connection Issues**
```python
# Connection health check
async def check_db_health() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False
```

#### **Service Communication Issues**
```python
# Retry pattern for service calls
async def call_with_retry(url: str, data: Dict, max_retries: int = 3) -> Dict:
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=30)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## 📝 Code Modification Guidelines

### **When Adding New Features**

1. **Follow Existing Patterns**: Use the same patterns as existing code
2. **Add Type Hints**: All new functions must have type annotations
3. **Include Logging**: Add structured logging for new operations
4. **Write Tests**: Include unit and integration tests
5. **Update Documentation**: Keep docs current with changes

### **When Modifying Existing Code**

1. **Understand Context**: Read related code and documentation first
2. **Preserve Interfaces**: Don't break existing API contracts
3. **Maintain Performance**: Ensure changes don't degrade performance
4. **Test Thoroughly**: Test both new and existing functionality
5. **Update Related Docs**: Keep documentation synchronized

### **When Integrating Services**

1. **Use Async Patterns**: All service calls should be asynchronous
2. **Handle Failures**: Implement proper error handling and retries
3. **Add Circuit Breakers**: Prevent cascade failures
4. **Monitor Performance**: Add metrics for service calls
5. **Document Integration**: Update integration documentation

## 🎯 Business Logic Patterns

### **Vehicle Matching Logic**
```python
# Multi-stage matching pattern
async def match_vehicle(self, vehicle_input: VehicleInput) -> MatchResult:
    # 1. Preprocess input
    preprocessed = self.preprocessor.preprocess(vehicle_input.description)
    
    # 2. Extract attributes with LLM
    llm_attributes = await self.llm_extractor.extract_attributes(vehicle_input.description)
    
    # 3. Combine attributes
    combined_attributes = self._combine_attributes(preprocessed['attributes'], llm_attributes)
    
    # 4. Find candidates
    candidates = self._find_candidates(vehicle_input.insurer_id, combined_attributes)
    
    # 5. Score candidates
    scored_candidates = await self._score_candidates(...)
    
    # 6. Select best match
    best_match = self._select_best_match(scored_candidates)
    
    # 7. Calculate confidence
    confidence_score = self._calculate_confidence(...)
    
    return MatchResult(...)
```

### **Database Transaction Pattern**
```python
# Repository transaction pattern
async def create_case_with_vehicles(
    self, 
    case_data: Dict, 
    vehicles_data: List[Dict]
) -> Case:
    try:
        # Create case
        case = await self.case_repo.create_case_with_cot(**case_data)
        
        # Create vehicles
        vehicles = await self.vehicle_repo.bulk_create_vehicles_with_cvegs(
            case.id, vehicles_data
        )
        
        # Update case vehicle count
        await self.case_repo.update(case.id, vehicle_count=len(vehicles))
        
        return case
        
    except Exception as e:
        # Transaction will be rolled back automatically
        logger.error("Failed to create case with vehicles", error=str(e))
        raise
```

### **Configuration Pattern**
```python
# Environment-based configuration
class Settings(BaseSettings):
    # Required settings
    openai_api_key: str
    database_url: str
    
    # Optional with defaults
    debug: bool = False
    log_level: str = "INFO"
    max_batch_size: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Usage in services
settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)
```

## 🚀 Performance Optimization

### **Batch Processing Optimization**
```python
# Efficient batch processing
async def process_large_batch(items: List[Item]) -> List[Result]:
    # Process in chunks to avoid memory issues
    chunk_size = 50
    results = []
    
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        chunk_results = await process_chunk(chunk)
        results.extend(chunk_results)
    
    return results
```

### **Database Query Optimization**
```python
# Efficient relationship queries
cases_with_vehicles = await db.execute(
    select(Case)
    .options(selectinload(Case.vehicles))  # Eager load
    .where(Case.status == "PROCESSED")
    .order_by(desc(Case.created_at))
    .limit(50)
)

# Avoid N+1 queries
vehicles = await db.execute(
    select(Vehicle)
    .join(Case)  # Join instead of separate queries
    .where(Case.client_name.ilike(f"%{client_name}%"))
)
```

### **Caching Strategy**
```python
# Multi-level caching
async def get_vehicle_match(description: str) -> MatchResult:
    # 1. Check memory cache
    if description in memory_cache:
        return memory_cache[description]
    
    # 2. Check Redis cache
    cached = await redis.get(f"match:{hash(description)}")
    if cached:
        result = MatchResult(**json.loads(cached))
        memory_cache[description] = result
        return result
    
    # 3. Compute result
    result = await compute_match(description)
    
    # 4. Cache result
    await redis.setex(f"match:{hash(description)}", 3600, result.json())
    memory_cache[description] = result
    
    return result
```

## 🔐 Security Patterns

### **Input Validation**
```python
# Comprehensive input validation
class SecureVehicleInput(BaseModel):
    description: str = Field(..., max_length=1000, regex=r'^[a-zA-Z0-9\s\-]+$')
    year: Optional[int] = Field(None, ge=1900, le=2030)
    
    @validator('description')
    def sanitize_description(cls, v):
        # Remove potentially harmful characters
        return re.sub(r'[<>"\']', '', v.strip())
```

### **Secure Configuration**
```python
# Secure settings management
class SecureSettings(BaseSettings):
    # Sensitive data from environment
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    database_password: str = Field(..., env="DB_PASSWORD")
    
    # Non-sensitive with defaults
    debug: bool = False
    
    @validator('openai_api_key')
    def validate_api_key(cls, v):
        if not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format')
        return v
```

## 📈 Monitoring and Metrics

### **Health Check Pattern**
```python
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_db_connection(),
        "redis": await check_redis_connection(),
        "openai": await check_openai_api(),
        "disk_space": check_disk_space()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### **Metrics Collection**
```python
# Performance metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log metrics
    logger.info("Request completed",
               method=request.method,
               path=request.url.path,
               status_code=response.status_code,
               process_time_ms=process_time * 1000)
    
    return response
```

This guide provides AI coding tools with the essential patterns and conventions needed to understand and modify the Minca AI Insurance Platform effectively.
