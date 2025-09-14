# System Architecture Overview

## Platform Vision

The Minca AI Insurance Platform is an intelligent underwriting automation system that transforms manual insurance processing into an automated, AI-powered workflow. The platform processes insurance requests from Outlook emails, extracts vehicle information, matches vehicles to CVEGS codes, and provides a complete case management interface.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Minca AI Insurance Platform                  │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Frontend      │  │   API Gateway   │  │   Load Balancer │ │
│  │                 │  │                 │  │                 │ │
│  │ • Next.js UI    │  │ • Rate Limiting │  │ • Health Checks │ │
│  │ • Case Mgmt     │  │ • Auth (Future) │  │ • SSL Term.     │ │
│  │ • Dashboard     │  │ • Request Route │  │ • Failover      │ │
│  │ • Excel Export  │  │ • Validation    │  │ • Monitoring    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                     │                     │         │
│           └─────────────────────┼─────────────────────┘         │
│                                 │                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Microservices Layer                      │ │
│  │                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │ │
│  │  │ Main API        │  │ Vehicle Codifier│  │ Document    │ │ │
│  │  │ Service         │  │ Service         │  │ Processor   │ │ │
│  │  │                 │  │                 │  │ Service     │ │ │
│  │  │ • Orchestration │  │ • CVEGS Match   │  │ • Excel Proc│ │ │
│  │  │ • Case Mgmt     │  │ • AI Matching   │  │ • Transform │ │ │
│  │  │ • Codify API    │  │ • Confidence    │  │ • Export    │ │ │
│  │  │ • File Upload   │  │ • Clean Arch    │  │ • Gcotiza   │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘ │ │
│  │           │                     │                     │     │ │
│  │           └─────────────────────┼─────────────────────┘     │ │
│  │                                 │                           │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │ │
│  │  │ Database        │  │ Workflow        │  │ Export      │ │ │
│  │  │ Service         │  │ Engine          │  │ Service     │ │ │
│  │  │                 │  │                 │  │             │ │ │
│  │  │ • Data Models   │  │ • Celery        │  │ • Excel Gen │ │ │
│  │  │ • Repositories  │  │ • Redis Queue   │  │ • PDF Gen   │ │ │
│  │  │ • COT Generator │  │ • Task Status   │  │ • Templates │ │ │
│  │  │ • Migrations    │  │ • Retry Logic   │  │ • Scheduling│ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                 │                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Data & Storage Layer                     │ │
│  │                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │ │
│  │  │   PostgreSQL    │  │   Redis Cache   │  │   Blob/S3   │ │ │
│  │  │                 │  │                 │  │   Storage   │ │ │
│  │  │ • Messages      │  │ • Session Cache │  │ • Email     │ │ │
│  │  │ • Cases         │  │ • Result Cache  │  │   Bodies    │ │ │
│  │  │ • Vehicles      │  │ • Job Queue     │  │ • Attach.   │ │ │
│  │  │ • Coverages     │  │ • Rate Limiting │  │ • CVEGS     │ │ │
│  │  │ • Attachments   │  │ • Temp Data     │  │   Datasets  │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                 │                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    External Services                        │ │
│  │                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │ │
│  │  │ Microsoft Graph │  │   OpenAI API    │  │   AWS       │ │ │
│  │  │                 │  │                 │  │   Services  │ │ │
│  │  │ • Outlook Mail  │  │ • GPT-4o-mini   │  │ • ECS       │ │ │
│  │  │ • Attachments   │  │ • Attribute     │  │ • RDS       │ │ │
│  │  │ • Webhooks      │  │   Extraction    │  │ • S3        │ │ │
│  │  │ • Notifications │  │ • Validation    │  │ • CloudWatch│ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. **Microservices Architecture**
- **Service Independence**: Each service can be developed, deployed, and scaled independently
- **Single Responsibility**: Each service has a focused, well-defined purpose
- **API-First Design**: Services communicate via well-defined REST APIs
- **Technology Flexibility**: Different services can use different tech stacks

### 2. **Event-Driven Processing**
- **Async Communication**: Services communicate via events and message queues
- **Decoupled Processing**: Services don't directly depend on each other's availability
- **Scalable Workflows**: Processing can scale based on demand
- **Fault Tolerance**: Failed processing can be retried without affecting other services

### 3. **AI-First Approach**
- **Intelligent Extraction**: LLM-powered data extraction from unstructured content
- **Confidence Scoring**: AI provides confidence levels for human review decisions
- **Continuous Learning**: System can be improved with feedback and new training data
- **Hybrid Intelligence**: Combines rule-based logic with AI for optimal accuracy

### 4. **Multi-Tenant Design**
- **Insurer Isolation**: Support multiple insurance companies with separate configurations
- **Configurable Rules**: Business rules and workflows per insurer
- **Data Segregation**: Secure data isolation between tenants
- **Scalable Onboarding**: Easy addition of new insurance companies

## Service Responsibilities

### **Main API Service** ✅ (Port 8000)
**Purpose**: Orchestration, case management, and workflow coordination
**Technology**: FastAPI + SQLAlchemy + PostgreSQL
**Responsibilities**:
- File upload and case creation
- Workflow orchestration across services
- API gateway for frontend integration
- Database operations and persistence

### **Document Processor Service** ✅ (Port 8001)  
**Purpose**: Excel/CSV processing, transformation, and export
**Technology**: FastAPI + openpyxl + pandas
**Responsibilities**:
- Extract data from uploaded Excel/CSV files
- Transform data using broker profiles
- Export to Gcotiza format with professional styling
- Background processing with real-time status

### **Vehicle Codifier Service** ✅ (Port 8002)
**Purpose**: AMIS/CVEGS vehicle matching and codification  
**Technology**: FastAPI + OpenAI + Clean Architecture + pgvector
**Responsibilities**:
- AI-powered vehicle description matching  
- Semantic search using embeddings and pgvector
- Batch processing with confidence scoring
- Clean Architecture with Domain-Driven Design
- Real-time API and background worker modes
- Multi-insurer support with configurable datasets

### **Database Layer** ✅ (packages/db)
**Purpose**: Unified data models and persistence across all services
**Technology**: PostgreSQL + SQLAlchemy + Alembic
**Responsibilities**:
- Shared data models (Case, Run, Row, Codify, Export)
- Database migrations and schema management
- Connection pooling and query optimization
- Cross-service data consistency
- Automatic COT number generation
- Database migrations and versioning

### **Smart Intake Service** ✅ (Port 8002)
**Purpose**: Process Outlook emails and extract vehicle information with AI-powered broker profile generation
**Technology**: FastAPI + Microsoft Graph + Celery + OpenAI
**Key Features**:
- **Manual email entry for testing workflows**
- **Hybrid broker profile system with auto-generation**
- **AI-assisted field mapping and validation**
- Microsoft Graph webhook integration (future)
- Email parsing and attachment processing
- Document intelligence (OCR, table extraction)
- Workflow orchestration

### **Document Intelligence Service** 🔄
**Purpose**: Extract structured data from documents (PDF, Excel, images)
**Technology**: FastAPI + OCR + pandas
**Key Features**:
- PDF text extraction and OCR
- Excel parsing and table detection
- Image processing and text recognition
- Structured data extraction

### **Frontend Application** ✅ (Port 3000)
**Purpose**: User interface for case management and intelligent broker profile management
**Technology**: Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui
**Key Features**:
- **Tabbed dashboard with manual email intake**
- **Broker profile management with AI-assisted generation**
- **3-step profile creation wizard**
- Case management dashboard
- Document viewer and editor
- Excel export functionality
- Real-time status updates

### **Export Service** 🔄
**Purpose**: Generate reports and export data in various formats
**Technology**: FastAPI + openpyxl + ReportLab
**Key Features**:
- Excel report generation
- PDF document creation
- Template management
- Scheduled exports

## Data Flow Architecture

### **Hybrid Broker Profile Workflow**

```
1. Email Entry (Manual/Smart Intake)
   │
   ▼
2. Broker Detection (Domain + Profile Registry)
   ├── Extract email domain
   ├── Check existing profiles
   ├── Apply known profile → Skip to Step 6
   └── No profile found → Continue
   │
   ▼
3. AI Schema Detection (LLM Analysis)
   ├── Analyze email content
   ├── Parse attachment headers
   ├── Extract field patterns
   └── Generate mapping suggestions
   │
   ▼
4. Profile Generation Wizard (Frontend)
   ├── Review AI suggestions
   ├── Edit field mappings
   ├── Validate requirements
   └── Create YAML profile
   │
   ▼
5. Profile Registry (Storage & Versioning)
   ├── Save profile to configs/broker-profiles/
   ├── Version in git
   ├── Tag with confidence scores
   └── Track usage statistics
   │
   ▼
6. Document Processing (Transform + Codify)
   ├── Apply broker profile rules
   ├── Transform to canonical format
   ├── Run vehicle matching
   └── Generate export-ready data
```

### **End-to-End Processing Flow**

```
1. Email Received (Manual Entry/Outlook)
   │
   ▼
2. Broker Profile Application
   ├── Detect broker from email domain
   ├── Apply existing profile OR
   ├── Generate new profile with AI
   └── Transform data to canonical format
   │
   ▼
3. Vehicle Matching (Vehicle Matcher Service)
   ├── Preprocess descriptions
   ├── Extract attributes with LLM
   ├── Match to CVEGS codes
   └── Calculate confidence scores
   │
   ▼
4. Data Persistence (Database Service)
   ├── Store case information
   ├── Save vehicle matches
   ├── Generate COT number
   └── Update processing status
   │
   ▼
5. User Review (Frontend Application)
   ├── Display case dashboard
   ├── Show matching results
   ├── Allow manual corrections
   └── Export final reports
```

### **Service Communication Patterns**

#### **Synchronous Communication**
- **API Calls**: Direct HTTP requests between services
- **Real-time Processing**: Immediate responses for user interactions
- **Data Queries**: Database lookups and updates

#### **Asynchronous Communication**
- **Event Queues**: Redis/SQS for background processing
- **Webhooks**: External system notifications (Microsoft Graph)
- **Batch Processing**: Large-scale data processing jobs

## Technology Stack

### **Backend Services**
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for session and result caching
- **Queue**: Celery with Redis broker
- **AI/ML**: OpenAI GPT-4o-mini, scikit-learn

### **Frontend**
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: React Query for server state
- **Charts**: Recharts for data visualization

### **Infrastructure**
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose (dev), Kubernetes/ECS (prod)
- **Cloud Platform**: AWS (ECS, RDS, ElastiCache, S3)
- **Infrastructure as Code**: Terraform
- **CI/CD**: GitHub Actions

### **External Services**
- **Email Integration**: Microsoft Graph API
- **AI Processing**: OpenAI API
- **Document Storage**: AWS S3 or Azure Blob Storage
- **Monitoring**: CloudWatch, Prometheus

## Security Architecture

### **Authentication & Authorization**
- **API Authentication**: JWT tokens with role-based access
- **Service-to-Service**: Internal API keys and service mesh
- **External APIs**: Secure credential management (AWS Secrets Manager)

### **Data Security**
- **Encryption**: TLS in transit, AES-256 at rest
- **PII Protection**: Data masking and anonymization
- **Audit Logging**: Comprehensive audit trails
- **Compliance**: GDPR and insurance industry standards

### **Network Security**
- **VPC Isolation**: Private subnets for backend services
- **API Gateway**: Centralized security policies
- **WAF Protection**: Web application firewall
- **DDoS Protection**: AWS Shield and CloudFlare

## Scalability Strategy

### **Horizontal Scaling**
- **Stateless Services**: All services designed for horizontal scaling
- **Load Balancing**: Application and network load balancers
- **Auto Scaling**: CPU/memory-based scaling policies
- **Database Scaling**: Read replicas and connection pooling

### **Performance Optimization**
- **Caching Strategy**: Multi-level caching (Redis, CDN, application)
- **Async Processing**: Non-blocking I/O for all operations
- **Batch Processing**: Efficient bulk operations
- **Resource Optimization**: Right-sized containers and instances

### **Data Scaling**
- **Database Partitioning**: Partition by insurer or date
- **Blob Storage**: Scalable file storage for documents
- **CDN**: Global content delivery for static assets
- **Data Archiving**: Automated data lifecycle management

## Monitoring & Observability

### **Application Monitoring**
- **Health Checks**: Comprehensive health endpoints
- **Metrics Collection**: Prometheus-compatible metrics
- **Distributed Tracing**: Request tracing across services
- **Error Tracking**: Centralized error logging and alerting

### **Infrastructure Monitoring**
- **Resource Utilization**: CPU, memory, disk, network monitoring
- **Service Discovery**: Automatic service registration and health checks
- **Log Aggregation**: Centralized logging with structured formats
- **Alerting**: Proactive alerts for system issues

### **Business Metrics**
- **Processing Metrics**: Email processing rates, matching accuracy
- **User Metrics**: Dashboard usage, case completion rates
- **Cost Metrics**: OpenAI API usage, infrastructure costs
- **Quality Metrics**: Confidence score distributions, review rates

## Deployment Architecture

### **Development Environment**
```
Docker Compose
├── vehicle-matcher (FastAPI)
├── database-service (FastAPI)
├── postgres (Database)
├── redis (Cache/Queue)
└── frontend (Next.js) [Future]
```

### **Production Environment (AWS)**
```
Route 53 (DNS)
     │
CloudFront (CDN)
     │
Application Load Balancer
     │
ECS Fargate Cluster
├── vehicle-matcher (Auto-scaling)
├── database-service (Auto-scaling)
├── intake-service (Auto-scaling) [Future]
├── document-intelligence (Auto-scaling) [Future]
└── export-service (Auto-scaling) [Future]
     │
┌────┴────────────────────────────┐
│                                 │
RDS PostgreSQL              ElastiCache Redis
(Multi-AZ)                  (Cluster Mode)
     │                           │
S3 Bucket                   CloudWatch
(Documents)                 (Monitoring)
```

## Integration Patterns

### **Service-to-Service Communication**
- **REST APIs**: HTTP/HTTPS with JSON payloads
- **Async Messaging**: Redis pub/sub for event notifications
- **Database Sharing**: Shared database with service-specific schemas
- **Configuration**: Environment-based service discovery

### **External System Integration**
- **Microsoft Graph**: OAuth 2.0 with refresh tokens
- **OpenAI API**: API key authentication with rate limiting
- **AWS Services**: IAM roles and service-linked roles
- **Monitoring Systems**: Webhook notifications and API integrations

## Disaster Recovery & Business Continuity

### **Backup Strategy**
- **Database Backups**: Automated daily backups with point-in-time recovery
- **File Backups**: S3 cross-region replication
- **Configuration Backups**: Infrastructure as Code in version control
- **Application Backups**: Container images in ECR

### **High Availability**
- **Multi-AZ Deployment**: Services deployed across availability zones
- **Database Clustering**: PostgreSQL with read replicas
- **Cache Clustering**: Redis cluster mode for high availability
- **Load Balancing**: Health check-based traffic routing

### **Recovery Procedures**
- **RTO Target**: < 4 hours for complete system recovery
- **RPO Target**: < 1 hour for data loss
- **Automated Failover**: Database and cache automatic failover
- **Manual Procedures**: Documented recovery procedures for complex scenarios

This architecture provides a robust, scalable foundation for the insurance underwriting automation platform while maintaining flexibility for future enhancements and integrations.
