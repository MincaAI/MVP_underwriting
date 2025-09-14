# Service Integration Guide

This document explains how services in the Minca AI Insurance Platform communicate and integrate with each other.

## Integration Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Smart Intake    │    │ Vehicle Matcher │    │ Database        │
│ Service         │    │ Service         │    │ Service         │
│                 │    │                 │    │                 │
│ Port: 8002      │────│ Port: 8000      │────│ Port: 8001      │
│                 │    │                 │    │                 │
│ • Email Parse   │    │ • CVEGS Match   │    │ • Data Models   │
│ • Attachments   │    │ • Batch Process │    │ • Repositories  │
│ • Workflow      │    │ • Confidence    │    │ • COT Generator │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   Database      │
                    │                 │
                    │ • Shared Schema │
                    │ • Transactions  │
                    │ • Audit Logs    │
                    └─────────────────┘
```

## Communication Patterns

### **1. Synchronous HTTP Communication**

Services communicate via REST APIs for real-time operations:

```python
# HTTP client pattern for service-to-service communication
class VehicleMatcherClient:
    def __init__(self, base_url: str = "http://vehicle-matcher:8000"):
        self.base_url = base_url
        self.timeout = httpx.Timeout(30.0)
    
    async def match_single_vehicle(self, vehicle: VehicleInput) -> MatchResult:
        """Match a single vehicle description."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/match/single",
                json=vehicle.dict()
            )
            response.raise_for_status()
            return MatchResult(**response.json())
    
    async def match_batch_vehicles(self, 
                                  vehicles: List[VehicleInput]) -> BatchMatchResponse:
        """Match multiple vehicles in batch."""
        batch_request = BatchMatchRequest(
            vehicles=vehicles,
            parallel_processing=True
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/match/batch",
                json=batch_request.dict()
            )
            response.raise_for_status()
            return BatchMatchResponse(**response.json())
```

### **2. Database-Mediated Communication**

Services share data through the database layer:

```python
# Database service client pattern
class DatabaseServiceClient:
    def __init__(self, base_url: str = "http://database-service:8001"):
        self.base_url = base_url
    
    async def create_case(self, case_data: Dict) -> Case:
        """Create a new insurance case."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/cases",
                json=case_data
            )
            response.raise_for_status()
            return Case(**response.json())
    
    async def add_vehicles_to_case(self, 
                                  case_id: str, 
                                  vehicles: List[Dict]) -> List[Vehicle]:
        """Add vehicles to an existing case."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/cases/{case_id}/vehicles",
                json={"vehicles": vehicles}
            )
            response.raise_for_status()
            return [Vehicle(**v) for v in response.json()]
```

### **3. Event-Driven Communication (Future)**

For asynchronous processing using Redis/SQS:

```python
# Event publishing pattern
class EventPublisher:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def publish_email_received(self, message_id: str, metadata: Dict):
        """Publish email received event."""
        event = {
            "event_type": "email_received",
            "message_id": message_id,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.publish("email_events", json.dumps(event))

# Event subscription pattern
class EventSubscriber:
    async def handle_email_received(self, event_data: Dict):
        """Handle email received event."""
        message_id = event_data["message_id"]
        
        # Process email
        await self.email_processor.process_email(message_id)
```

## Integration Workflows

### **Email Processing Workflow**

```python
# Complete email processing integration
class EmailProcessingWorkflow:
    def __init__(self):
        self.vehicle_matcher = VehicleMatcherClient()
        self.database_client = DatabaseServiceClient()
        self.document_processor = DocumentProcessor()
    
    async def process_email(self, message_id: str):
        """Complete email processing workflow."""
        
        # 1. Parse email and create case
        email_data = await self.parse_email(message_id)
        case = await self.database_client.create_case(email_data)
        
        # 2. Process attachments
        attachments = await self.process_attachments(email_data.attachments)
        
        # 3. Extract vehicle information
        vehicles_data = await self.extract_vehicles(email_data, attachments)
        
        # 4. Match vehicles to CVEGS codes
        vehicle_inputs = [VehicleInput(**v) for v in vehicles_data]
        match_results = await self.vehicle_matcher.match_batch_vehicles(vehicle_inputs)
        
        # 5. Store results in database
        vehicles = []
        for vehicle_data, match_result in zip(vehicles_data, match_results.results):
            vehicle_data["cvegs_result"] = match_result.dict()
            vehicles.append(vehicle_data)
        
        stored_vehicles = await self.database_client.add_vehicles_to_case(
            case.id, vehicles
        )
        
        # 6. Update case status
        await self.database_client.update_case_status(
            case.id, 
            status="PROCESSED",
            confidence=self.calculate_overall_confidence(match_results)
        )
        
        return case
```

### **Vehicle Matching Integration**

```python
# Integration between intake and vehicle matcher
class VehicleMatchingIntegration:
    async def process_vehicle_list(self, 
                                  case_id: str,
                                  vehicle_descriptions: List[str]) -> List[Vehicle]:
        """Process a list of vehicle descriptions."""
        
        # 1. Prepare vehicle inputs
        vehicle_inputs = [
            VehicleInput(description=desc, insurer_id="default")
            for desc in vehicle_descriptions
        ]
        
        # 2. Call vehicle matcher service
        batch_response = await self.vehicle_matcher.match_batch_vehicles(vehicle_inputs)
        
        # 3. Process results
        vehicles = []
        for i, result in enumerate(batch_response.results):
            vehicle_data = {
                "case_id": case_id,
                "original_description": vehicle_descriptions[i],
                "brand": result.matched_brand,
                "model": result.matched_model,
                "year": result.matched_year,
                "cvegs_code": result.cvegs_code,
                "cvegs_confidence": result.confidence_score,
                "cvegs_matched_description": result.matched_description,
                "extracted_attributes": json.dumps(result.extracted_attributes.dict()),
                "processing_warnings": json.dumps(result.warnings)
            }
            
            vehicle = await self.database_client.create_vehicle(vehicle_data)
            vehicles.append(vehicle)
        
        return vehicles
```

## Error Handling and Resilience

### **Circuit Breaker Pattern**

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

# Usage in service integration
vehicle_matcher_breaker = CircuitBreaker()

async def safe_vehicle_match(vehicle_input: VehicleInput) -> MatchResult:
    return await vehicle_matcher_breaker.call(
        vehicle_matcher.match_single_vehicle,
        vehicle_input
    )
```

### **Retry Pattern with Exponential Backoff**

```python
async def call_with_retry(
    func,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
):
    """Call function with exponential backoff retry."""
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                logger.error("Max retries exceeded", 
                           function=func.__name__,
                           attempts=attempt + 1,
                           error=str(e))
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning("Retry attempt",
                          function=func.__name__,
                          attempt=attempt + 1,
                          delay=delay,
                          error=str(e))
            
            await asyncio.sleep(delay)
```

## Service Discovery

### **Environment-Based Discovery**

```python
# Service URL configuration
class ServiceURLs(BaseSettings):
    vehicle_matcher_url: str = "http://vehicle-matcher:8000"
    database_service_url: str = "http://database-service:8001"
    intake_service_url: str = "http://intake-service:8002"
    
    class Config:
        env_prefix = "SERVICE_"

# Usage
urls = ServiceURLs()
vehicle_matcher = VehicleMatcherClient(urls.vehicle_matcher_url)
```

### **Health Check Integration**

```python
# Service health monitoring
class ServiceHealthChecker:
    def __init__(self, service_urls: ServiceURLs):
        self.service_urls = service_urls
    
    async def check_all_services(self) -> Dict[str, bool]:
        """Check health of all services."""
        services = {
            "vehicle_matcher": self.service_urls.vehicle_matcher_url,
            "database_service": self.service_urls.database_service_url,
        }
        
        health_status = {}
        
        for service_name, url in services.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url}/health", timeout=5.0)
                    health_status[service_name] = response.status_code == 200
            except Exception as e:
                logger.error("Health check failed", 
                           service=service_name, 
                           error=str(e))
                health_status[service_name] = False
        
        return health_status
```

## Data Consistency

### **Transaction Coordination**

```python
# Distributed transaction pattern (simplified)
class TransactionCoordinator:
    async def create_case_with_matching(self, 
                                       email_data: Dict,
                                       vehicle_descriptions: List[str]) -> Case:
        """Create case and match vehicles in coordinated transaction."""
        
        # Start database transaction
        async with self.db.begin() as transaction:
            try:
                # 1. Create case
                case = await self.case_repo.create_case_with_cot(**email_data)
                
                # 2. Match vehicles (external service call)
                vehicle_inputs = [VehicleInput(description=desc) for desc in vehicle_descriptions]
                match_results = await self.vehicle_matcher.match_batch_vehicles(vehicle_inputs)
                
                # 3. Store vehicle results
                vehicles = []
                for desc, result in zip(vehicle_descriptions, match_results.results):
                    vehicle_data = {
                        "case_id": case.id,
                        "original_description": desc,
                        "cvegs_result": result.dict()
                    }
                    vehicle = await self.vehicle_repo.create_vehicle_with_cvegs(
                        case.id, vehicle_data, result.dict()
                    )
                    vehicles.append(vehicle)
                
                # 4. Update case with vehicle count
                await self.case_repo.update(case.id, vehicle_count=len(vehicles))
                
                # Commit transaction
                await transaction.commit()
                
                logger.info("Case created with vehicles", 
                           case_id=case.id,
                           vehicle_count=len(vehicles))
                
                return case
                
            except Exception as e:
                # Transaction will be rolled back automatically
                logger.error("Failed to create case with matching", error=str(e))
                raise
```

## API Versioning

### **Version Management**

```python
# API versioning pattern
@app.get("/v1/match/single")
async def match_single_v1(vehicle: VehicleInputV1) -> MatchResultV1:
    """Version 1 of single vehicle matching."""
    pass

@app.get("/v2/match/single")
async def match_single_v2(vehicle: VehicleInputV2) -> MatchResultV2:
    """Version 2 with enhanced features."""
    pass

# Version-aware client
class VersionedClient:
    def __init__(self, base_url: str, api_version: str = "v1"):
        self.base_url = base_url
        self.api_version = api_version
    
    async def match_vehicle(self, vehicle: VehicleInput) -> MatchResult:
        url = f"{self.base_url}/{self.api_version}/match/single"
        # ... implementation
```

## Authentication and Authorization (Future)

### **JWT Token Pattern**

```python
# JWT authentication middleware
async def verify_jwt_token(request: Request):
    """Verify JWT token in request headers."""
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    try:
        payload = jwt.decode(token[7:], SECRET_KEY, algorithms=["HS256"])
        request.state.user_id = payload.get("user_id")
        request.state.permissions = payload.get("permissions", [])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Protected endpoint
@app.post("/protected-endpoint")
async def protected_endpoint(
    request: Request,
    user: dict = Depends(verify_jwt_token)
):
    # Endpoint logic with authenticated user
    pass
```

### **Service-to-Service Authentication**

```python
# Internal service authentication
class InternalServiceAuth:
    def __init__(self, service_key: str):
        self.service_key = service_key
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for internal service calls."""
        return {
            "X-Service-Key": self.service_key,
            "X-Service-Name": "intake-service"
        }

# Usage in service calls
auth = InternalServiceAuth(settings.internal_service_key)
headers = auth.get_auth_headers()

async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data, headers=headers)
```

## Rate Limiting and Throttling

### **Rate Limiting Pattern**

```python
# Rate limiting for external API calls
class RateLimiter:
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self):
        """Acquire rate limit token."""
        now = time.time()
        
        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            await asyncio.sleep(sleep_time)
        
        self.requests.append(now)

# Usage with OpenAI API
openai_rate_limiter = RateLimiter(max_requests=50, time_window=60)

async def call_openai_with_rate_limit(prompt: str) -> str:
    await openai_rate_limiter.acquire()
    return await openai_client.chat.completions.create(...)
```

## Monitoring and Observability

### **Distributed Tracing**

```python
# Request tracing across services
import uuid

class RequestTracer:
    @staticmethod
    def generate_trace_id() -> str:
        """Generate unique trace ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_trace_headers(trace_id: str) -> Dict[str, str]:
        """Get headers for request tracing."""
        return {
            "X-Trace-ID": trace_id,
            "X-Request-ID": str(uuid.uuid4())
        }

# Usage in service calls
trace_id = RequestTracer.generate_trace_id()
headers = RequestTracer.get_trace_headers(trace_id)

# Log with trace context
logger.info("Starting vehicle matching", 
           trace_id=trace_id,
           vehicle_count=len(vehicles))

# Pass trace ID to other services
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data, headers=headers)
```

### **Service Metrics**

```python
# Metrics collection for service integration
class ServiceMetrics:
    def __init__(self):
        self.call_counts = {}
        self.response_times = {}
        self.error_counts = {}
    
    async def record_service_call(self, 
                                 service_name: str,
                                 endpoint: str,
                                 response_time: float,
                                 success: bool):
        """Record service call metrics."""
        key = f"{service_name}:{endpoint}"
        
        self.call_counts[key] = self.call_counts.get(key, 0) + 1
        
        if key not in self.response_times:
            self.response_times[key] = []
        self.response_times[key].append(response_time)
        
        if not success:
            self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Log metrics
        logger.info("Service call metrics",
                   service=service_name,
                   endpoint=endpoint,
                   response_time_ms=response_time * 1000,
                   success=success)
```

## Configuration Management

### **Service Configuration**

```python
# Centralized configuration for service integration
class IntegrationConfig(BaseSettings):
    # Service URLs
    vehicle_matcher_url: str = "http://vehicle-matcher:8000"
    database_service_url: str = "http://database-service:8001"
    
    # Timeouts
    service_timeout: int = 30
    batch_timeout: int = 300
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Rate limiting
    openai_rate_limit: int = 50
    service_rate_limit: int = 100
    
    class Config:
        env_prefix = "INTEGRATION_"

# Usage across services
config = IntegrationConfig()
```

## Testing Integration

### **Integration Test Patterns**

```python
# End-to-end integration test
@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete email processing workflow."""
    
    # 1. Create test email data
    email_data = {
        "subject": "Fleet Insurance Request",
        "from_email": "broker@example.com",
        "vehicle_descriptions": ["TOYOTA YARIS 2020", "HONDA CIVIC 2021"]
    }
    
    # 2. Process email
    workflow = EmailProcessingWorkflow()
    case = await workflow.process_email("test_message_id")
    
    # 3. Verify results
    assert case.cot_number is not None
    assert case.vehicle_count == 2
    
    # 4. Check vehicles were matched
    vehicles = await database_client.get_vehicles_by_case(case.id)
    assert len(vehicles) == 2
    assert all(v.cvegs_code is not None for v in vehicles)

# Service mock for testing
@pytest.fixture
async def mock_vehicle_matcher():
    """Mock vehicle matcher service for testing."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "cvegs_code": "12345",
                    "confidence_score": 0.95,
                    "matched_brand": "TOYOTA",
                    "matched_model": "YARIS"
                }
            ]
        }
        mock_post.return_value = mock_response
        yield mock_post
```

This integration guide provides the patterns and examples needed for AI tools to understand and implement service communication in the Minca AI Insurance Platform.
