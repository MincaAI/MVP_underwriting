# Smart Intake Service Documentation

The Smart Intake Service is the email processing component that connects Outlook emails to the insurance underwriting workflow. It handles real-time email notifications, extracts vehicle information, and orchestrates the complete processing pipeline.

## Service Overview

### **Purpose**
- Process Outlook emails from the "Fleet Auto" folder in real-time
- Extract vehicle information and case details from email content and attachments
- Orchestrate workflow between email processing, vehicle matching, and database storage
- Provide background processing with retry logic and error handling

### **Technology Stack**
- **Framework**: FastAPI (Python 3.11+)
- **Email Integration**: Microsoft Graph API with OAuth 2.0
- **Task Queue**: Celery with Redis broker
- **Document Processing**: BeautifulSoup, html2text, pandas
- **AI Integration**: OpenAI for document intelligence
- **Storage**: Local filesystem or S3 for attachments

### **Port**: 8002 (configurable)

## Architecture

### **Service Components**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Smart Intake Service                         │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Microsoft Graph │  │ Email Processor │  │ Task Queue      │ │
│  │ Integration     │  │                 │  │                 │ │
│  │                 │  │ • Content Parse │  │ • Celery        │ │
│  │ • OAuth 2.0     │  │ • Pattern Match │  │ • Redis Broker  │ │
│  │ • Webhooks      │  │ • Table Extract │  │ • Retry Logic   │ │
│  │ • Subscriptions │  │ • Data Clean    │  │ • Status Track  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                     │                     │         │
│           └─────────────────────┼─────────────────────┘         │
│                                 │                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Document        │  │ Service         │  │ Workflow        │ │
│  │ Intelligence    │  │ Integration     │  │ Orchestration   │ │
│  │                 │  │                 │  │                 │ │
│  │ • PDF OCR       │  │ • Vehicle       │  │ • Email→Match   │ │
│  │ • Excel Parse   │  │   Matcher       │  │ • Match→Store   │ │
│  │ • Table Detect  │  │ • Database      │  │ • Error Handle  │ │
│  │ • Text Extract  │  │   Client        │  │ • Status Update │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Email Processing Pipeline

### **Complete Workflow**

```
1. Email Received (Outlook "Fleet Auto" folder)
   │
   ▼
2. Microsoft Graph Webhook Notification
   │
   ▼
3. Webhook Handler (FastAPI endpoint)
   ├── Validate webhook signature
   ├── Extract message ID
   └── Queue background task
   │
   ▼
4. Celery Background Task
   ├── Fetch email from Graph API
   ├── Create message record in database
   ├── Process email content (HTML→text, tables)
   ├── Process attachments (Excel, PDF)
   ├── Extract vehicle descriptions
   ├── Extract case information (client, broker)
   └── Continue to vehicle matching
   │
   ▼
5. Vehicle Matching Integration
   ├── Call Vehicle Matcher Service
   ├── Process batch results
   └── Calculate overall confidence
   │
   ▼
6. Database Storage
   ├── Create case with auto-generated COT
   ├── Store vehicles with CVEGS results
   ├── Update message status
   └── Set confidence and missing fields
```

## Microsoft Graph Integration

### **OAuth 2.0 Setup**
```python
class GraphTokenManager:
    def __init__(self):
        self.app = ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=settings.azure_client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}"
        )
    
    async def get_access_token(self) -> str:
        # Automatic token refresh with MSAL
        if self._is_token_valid():
            return self._access_token
        
        # Refresh token if needed
        await self._refresh_access_token()
        return self._access_token
```

### **Webhook Handling**
```python
@app.post("/graph/notifications")
async def handle_graph_notification(payload: GraphNotification):
    for notification in payload.value:
        message_id = notification.resourceData.get("id")
        
        # Queue background processing
        process_email_task.delay(
            message_id=message_id,
            change_type=notification.changeType
        )
    
    return {"received": True}
```

### **Email Fetching**
```python
class GraphAPIClient:
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        headers = await self._get_headers()
        url = f"{self.base_url}/me/messages/{message_id}?$expand=attachments"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            return response.json()
```

## Email Processing

### **Content Extraction**
```python
class EmailProcessor:
    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Extract metadata
        metadata = self._extract_email_metadata(email_data)
        
        # 2. Process body content
        body_content = self._process_email_body(email_data)
        
        # 3. Extract structured information
        extracted_info = self._extract_structured_info(body_content)
        
        return {
            "metadata": metadata,
            "body_content": body_content,
            "extracted_info": extracted_info
        }
```

### **Pattern Recognition**
```python
# Client information patterns
self.client_patterns = {
    'client_name': [
        r'(?:CLIENTE|CLIENT|ASEGURADO):\s*([A-Z\s\.]+)',
        r'(?:RAZÓN SOCIAL|COMPANY):\s*([A-Z\s\.]+)'
    ],
    'client_rfc': [
        r'(?:RFC):\s*([A-Z0-9]{10,13})',
        r'\b([A-Z]{3,4}\d{6}[A-Z0-9]{3})\b'
    ],
    'broker_email': [
        r'(?:EMAIL|CORREO):\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    ]
}

# Vehicle description extraction
def _extract_vehicle_descriptions_from_text(self, text: str) -> List[str]:
    # Pattern matching for vehicle descriptions
    # Table extraction from HTML
    # Duplicate removal and cleaning
```

## Celery Task System

### **Background Processing**
```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_email_task(self, message_id: str, change_type: str = "created"):
    try:
        # Complete async email processing
        result = asyncio.run(_process_email_async(
            message_id=message_id,
            change_type=change_type,
            task_id=self.request.id
        ))
        
        return {"success": True, "result": result}
        
    except Exception as exc:
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=retry_delay)
        
        return {"success": False, "error": str(exc)}
```

### **Task Monitoring**
```python
# Celery signal handlers for comprehensive monitoring
@celery_app.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwds):
    TaskStatus.log_task_start(task.name, task_id)

@celery_app.task_success.connect
def task_success_handler(sender=None, task_id=None, runtime=None, **kwds):
    TaskStatus.log_task_success(sender.name, task_id, runtime)
```

## Service Integration

### **Vehicle Matcher Integration**
```python
class VehicleMatcherClient:
    async def match_batch_vehicles(self, vehicle_inputs: List[Dict]) -> Dict:
        batch_request = {
            "vehicles": vehicle_inputs,
            "parallel_processing": True
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/match/batch",
                json=batch_request
            )
            return response.json()
```

### **Database Integration**
```python
class DatabaseClient:
    async def create_case_with_vehicles(self, 
                                       message_id: str,
                                       case_data: Dict,
                                       vehicle_descriptions: List[str],
                                       match_results: List[Dict]) -> Dict:
        # Direct database access using repositories
        async with AsyncSessionLocal() as db:
            case_repo = CaseRepository(db)
            vehicle_repo = VehicleRepository(db)
            
            # Create case with auto-generated COT
            case = await case_repo.create_case_with_cot(**case_data)
            
            # Create vehicles with CVEGS results
            vehicles = await vehicle_repo.bulk_create_vehicles_with_cvegs(
                case.id, vehicles_data
            )
            
            return case.to_dict()
```

## Configuration

### **Environment Variables**
```bash
# Microsoft Graph Configuration
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_REDIRECT_URI=https://api.yourdomain.com/oauth/callback

# Webhook Configuration
WEBHOOK_BASE_URL=https://api.yourdomain.com
WEBHOOK_SECRET=your_webhook_secret
TARGET_FOLDER_NAME="Fleet Auto"

# Service Integration
VEHICLE_MATCHER_URL=http://vehicle-matcher:8000
DATABASE_SERVICE_URL=http://database-service:8001

# Celery Configuration
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# OpenAI Configuration (for document intelligence)
OPENAI_API_KEY=your_openai_api_key
```

### **Azure App Registration Setup**
1. **Create App Registration** in Azure Entra ID
2. **Set Redirect URI**: `https://api.yourdomain.com/oauth/callback`
3. **Configure API Permissions**:
   - `Mail.Read` (Delegated)
   - `MailboxSettings.Read` (Delegated)
   - `offline_access` (Delegated)
4. **Admin Consent**: Grant admin consent for permissions
5. **Create Client Secret**: Generate and store securely

### **Outlook Folder Setup**
1. **Create Folder**: Create "Fleet Auto" folder in Outlook
2. **Create Rule**: Set up rule to move fleet insurance emails to this folder
3. **Test Setup**: Send test email to verify folder detection

## Development

### **Local Development**
```bash
# Setup
cd services/smart-intake-service
cp .env.example .env
# Edit .env with your Azure and OpenAI credentials

# Install dependencies
pip install -r requirements.txt

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start FastAPI service
python -m uvicorn app.main:app --reload --port 8002
```

### **Testing**
```python
# Test email processing
@pytest.mark.asyncio
async def test_email_processing():
    processor = EmailProcessor()
    
    # Mock email data
    email_data = {
        "id": "test_message_id",
        "subject": "Fleet Insurance Request",
        "body": {"content": "TOYOTA YARIS SOL L 2020", "contentType": "text"}
    }
    
    result = await processor.process_email(email_data)
    
    assert "extracted_info" in result
    assert "vehicle_descriptions" in result["extracted_info"]

# Test webhook handling
def test_webhook_validation():
    handler = GraphWebhookHandler()
    
    # Test validation token
    token = handler.handle_validation("test_token")
    assert token == "test_token"
```

## Monitoring

### **Health Checks**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "graph_api": await check_graph_connection(),
            "celery": check_celery_health(),
            "redis": await check_redis_connection(),
            "vehicle_matcher": await vehicle_matcher.check_health(),
            "database": await database_client.check_health()
        }
    }
```

### **Task Monitoring**
```python
@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "progress": result.info if result.state == "PROGRESS" else None
    }
```

## Integration Examples

### **Complete Email Processing**
```python
# End-to-end email processing workflow
async def process_email_workflow(message_id: str):
    # 1. Fetch email from Graph API
    email_data = await graph_client.get_message(message_id)
    
    # 2. Create message record
    message = await database_client.create_or_update_message(
        provider_id=message_id,
        email_data=email_data,
        status="PROCESSING"
    )
    
    # 3. Process email content
    processed_email = await email_processor.process_email(email_data)
    
    # 4. Extract vehicle descriptions
    vehicles = await email_processor.extract_vehicle_descriptions(
        processed_email, []
    )
    
    # 5. Match vehicles to CVEGS codes
    match_results = await vehicle_matcher.match_batch_vehicles([
        {"description": desc, "insurer_id": "default"}
        for desc in vehicles
    ])
    
    # 6. Extract case information
    case_data = await email_processor.extract_case_information(
        processed_email, []
    )
    
    # 7. Create case with vehicles
    case = await database_client.create_case_with_vehicles(
        message["id"], case_data, vehicles, match_results["results"]
    )
    
    # 8. Update message status
    overall_confidence = calculate_overall_confidence(match_results["results"])
    final_status = "PROCESSED" if overall_confidence >= 0.7 else "NEEDS_REVIEW"
    
    await database_client.update_message_status(
        message["id"], final_status, case["cot_number"], overall_confidence
    )
    
    return {
        "success": True,
        "cot_number": case["cot_number"],
        "vehicle_count": len(vehicles),
        "overall_confidence": overall_confidence
    }
```

## Error Handling

### **Retry Logic**
```python
# Exponential backoff for failed tasks
@celery_app.task(bind=True, max_retries=3)
def process_email_task(self, message_id: str):
    try:
        return process_email_workflow(message_id)
    except Exception as exc:
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=retry_delay)
        
        # Update message status to ERROR
        await database_client.update_message_status(message_id, "ERROR")
        raise
```

### **Graceful Degradation**
```python
# Handle service failures gracefully
async def safe_vehicle_matching(vehicles: List[str]) -> List[Dict]:
    try:
        return await vehicle_matcher.match_batch_vehicles(vehicles)
    except Exception as e:
        logger.error("Vehicle matching failed", error=str(e))
        
        # Return error results for all vehicles
        return {
            "results": [
                {"cvegs_code": "ERROR", "confidence_score": 0.0, "error": str(e)}
                for _ in vehicles
            ],
            "summary": {"success_rate": 0.0, "total_vehicles": len(vehicles)}
        }
```

## Performance Optimization

### **Async Processing**
- All I/O operations use async/await patterns
- Concurrent processing of attachments
- Parallel vehicle matching integration
- Non-blocking webhook responses

### **Caching Strategy**
- Redis caching for frequently accessed data
- Token caching to avoid repeated OAuth flows
- Result caching for duplicate email processing
- Attachment caching to avoid re-downloading

### **Resource Management**
- Configurable concurrency limits
- Memory-efficient file processing
- Automatic cleanup of temporary files
- Connection pooling for external APIs

## Troubleshooting

### **Common Issues**

#### **Microsoft Graph Errors**
- **Token Expiration**: Automatic refresh with MSAL
- **Permission Issues**: Verify API permissions and admin consent
- **Webhook Validation**: Check webhook secret and signature validation

#### **Email Processing Issues**
- **No Vehicle Descriptions**: Check pattern matching and content extraction
- **Attachment Processing**: Verify file types and size limits
- **Character Encoding**: Handle different email encodings properly

#### **Integration Issues**
- **Service Timeouts**: Configure appropriate timeout values
- **Network Errors**: Implement retry logic with exponential backoff
- **Database Errors**: Handle connection issues and transaction rollbacks

### **Debug Mode**
```bash
# Enable detailed logging
DEBUG=true
LOG_LEVEL=DEBUG

# Monitor Celery tasks
celery -A app.tasks.celery_app flower

# View task logs
docker-compose logs -f smart-intake-service
```

This Smart Intake Service provides the critical link between Outlook email processing and the insurance underwriting workflow, enabling complete automation of the intake process.
