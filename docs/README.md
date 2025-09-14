# Minca AI Insurance Platform - Documentation

Welcome to the comprehensive documentation for the Minca AI Insurance Platform. This documentation is designed to help developers, AI coding tools, and stakeholders understand the complete system architecture and implementation.

## 🎯 Platform Overview

The Minca AI Insurance Platform is an intelligent underwriting automation system that processes insurance requests from Outlook emails, extracts vehicle information, matches vehicles to CVEGS codes, and provides a complete case management interface.

## 📁 Documentation Structure

```
docs/
├── README.md                    # This file - main documentation hub
├── architecture/
│   ├── system-overview.md       # Complete platform architecture
│   ├── microservices.md         # Service interactions and communication
│   ├── data-flow.md             # End-to-end data processing flow
│   └── integration-patterns.md  # How services integrate
├── services/
│   ├── vehicle-matcher.md       # Vehicle CVEGS matching service overview
│   ├── vehicle-matcher/         # Complete vehicle matcher documentation
│   │   ├── README.md           # Service documentation overview
│   │   ├── api/                # API endpoints and specifications
│   │   ├── architecture/       # Service architecture details
│   │   ├── development/        # Development setup and guides
│   │   └── deployment/         # Deployment instructions
│   ├── database-layer.md        # Database layer (packages/db)
│   ├── intake-service.md        # Outlook email processing (future)
│   └── frontend.md              # Next.js user interface (future)
├── database/
│   ├── schema.md                # Complete database schema
│   ├── relationships.md         # Entity relationships and constraints
│   ├── migrations.md            # Database migration procedures
│   └── queries.md               # Common query patterns
├── deployment/
│   ├── docker.md                # Docker deployment guide
│   ├── aws.md                   # AWS cloud deployment
│   ├── ci-cd.md                 # CI/CD pipeline setup
│   └── monitoring.md            # Monitoring and observability
├── development/
│   ├── getting-started.md       # Quick start for developers
│   ├── coding-standards.md      # Code conventions and patterns
│   ├── testing.md               # Testing strategies and examples
│   └── ai-tool-guide.md         # Guide for AI coding tools
└── api/
    ├── overview.md              # API design principles
    ├── authentication.md        # Authentication patterns (future)
    └── integration.md           # Inter-service communication
```

## 🚀 Quick Start for AI Tools

### **Understanding the System**
1. **Start here**: [System Overview](architecture/system-overview.md)
2. **Service details**: [Microservices Architecture](architecture/microservices.md)
3. **Data flow**: [Data Processing Pipeline](architecture/data-flow.md)

### **Working with Services**
1. **Vehicle Matcher**: [Service Documentation](services/vehicle-matcher.md) | [Complete Docs](services/vehicle-matcher/)
2. **Database Layer**: [Data Models and Repositories](services/database-layer.md)
3. **Smart Intake**: [Email Processing Service](services/smart-intake-service.md)
4. **Frontend**: [Next.js Application](services/frontend.md)
5. **API Integration**: [Service Communication](api/integration.md)

### **Development Tasks**
1. **Setup**: [Getting Started Guide](development/getting-started.md)
2. **Patterns**: [Coding Standards](development/coding-standards.md)
3. **Testing**: [Test Strategies](development/testing.md)

## 🏗️ Current Implementation Status

### **✅ Completed Services**

#### **Vehicle CVEGS Matcher Service** (Port 8000)
- **Purpose**: Match vehicle descriptions to CVEGS codes using AI
- **Technology**: FastAPI + OpenAI + scikit-learn
- **Features**: Batch processing, multi-insurer support, confidence scoring
- **Status**: Production-ready with comprehensive documentation

#### **Database Layer** (PostgreSQL + packages/db)
- **Purpose**: Data persistence and management for the platform
- **Technology**: PostgreSQL + SQLAlchemy + Alembic
- **Features**: Complete schema, migrations, shared models
- **Status**: Unified implementation with current workflow models

#### **Smart Intake Service** (Port 8002)
- **Purpose**: Process Outlook emails and extract vehicle information
- **Technology**: FastAPI + Microsoft Graph + Celery + Redis
- **Features**: Real-time webhooks, intelligent extraction, workflow orchestration
- **Status**: Core implementation complete with email processing pipeline

#### **Frontend Application** (Port 3000)
- **Purpose**: User interface for case management and review
- **Technology**: Next.js 14 + TypeScript + Tailwind CSS + React Query
- **Features**: Dashboard, case management, vehicle grid, export functionality
- **Status**: Foundation complete with dashboard and API integration

### **🔄 Planned Services**

#### **Smart Intake Service** (Phase 3)
- **Purpose**: Process Outlook emails and extract vehicle information
- **Technology**: FastAPI + Microsoft Graph + Celery
- **Timeline**: 3-4 weeks

#### **Frontend Application** (Phase 4)
- **Purpose**: User interface for case management and review
- **Technology**: Next.js + TypeScript + Tailwind CSS
- **Timeline**: 4-5 weeks

#### **AWS Deployment** (Phase 5)
- **Purpose**: Production cloud infrastructure
- **Technology**: Terraform + ECS + RDS + ElastiCache
- **Timeline**: 2-3 weeks

## 🎯 Platform Capabilities

### **Current Features**
- ✅ **Vehicle Matching**: High-accuracy CVEGS code matching with confidence scoring
- ✅ **Batch Processing**: Process up to 200 vehicles in parallel
- ✅ **Data Persistence**: Complete database schema with audit trails
- ✅ **COT Generation**: Automatic case identifier generation (TK-YYYY-NNN)
- ✅ **Multi-Insurer Support**: Configuration-driven insurer management
- ✅ **API Documentation**: Comprehensive OpenAPI specifications

### **Future Features**
- 🔄 **Email Processing**: Automatic Outlook email intake and parsing
- 🔄 **Document Intelligence**: PDF and Excel document processing
- 🔄 **User Interface**: Web-based case management dashboard
- 🔄 **Cloud Deployment**: Scalable AWS infrastructure
- 🔄 **Workflow Automation**: End-to-end processing automation

## 🤖 AI Tool Integration

### **Key Files for Understanding**
```
# Core Services
services/vehicle-codifier/src/vehicle_codifier/main.py  # Vehicle codification API
services/api/src/api/                                    # Main API orchestration
packages/db/src/app/db/models.py                        # Database models

# Configuration
services/*/app/config/settings.py             # Service configurations
services/*/requirements.txt                   # Dependencies

# Documentation
docs/                                         # This documentation
services/vehicle-matcher/docs/                # Service-specific docs
```

### **Common Development Patterns**
- **FastAPI**: Async web framework with Pydantic validation
- **Repository Pattern**: Data access abstraction with business logic
- **Dependency Injection**: Service dependencies via FastAPI
- **Structured Logging**: Request tracing and performance monitoring
- **Docker Containerization**: Consistent deployment across environments

### **Code Conventions**
- **Type Hints**: All functions use Python type annotations
- **Async/Await**: All I/O operations are asynchronous
- **Pydantic Models**: Data validation and serialization
- **Error Handling**: Comprehensive exception handling with proper HTTP codes

## 📊 System Metrics

### **Performance Targets**
- **Vehicle Matching**: < 300ms per vehicle
- **Batch Processing**: < 100ms per vehicle (parallel)
- **Database Operations**: < 50ms for simple queries
- **API Response Time**: < 200ms for most endpoints

### **Quality Metrics**
- **Match Accuracy**: > 90% for high-confidence matches
- **System Uptime**: > 99.9% availability target
- **Error Rate**: < 1% for normal operations
- **Test Coverage**: > 80% code coverage

## 🔧 Development Workflow

### **For AI Coding Tools**
1. **Understand Architecture**: Read system overview and service docs
2. **Follow Patterns**: Use established code patterns and conventions
3. **Add Tests**: Include comprehensive tests for new functionality
4. **Update Docs**: Keep documentation current with changes
5. **Monitor Performance**: Ensure changes meet performance targets

### **Common Tasks**
- **Adding Endpoints**: Follow FastAPI patterns with Pydantic validation
- **Database Changes**: Use Alembic migrations and repository pattern
- **Service Integration**: Use async HTTP clients with proper error handling
- **Configuration**: Use environment-based settings with validation

## 🚀 Getting Started

### **For Developers**
1. **Read**: [Getting Started Guide](development/getting-started.md)
2. **Setup**: Follow service-specific setup instructions
3. **Explore**: Use API documentation and examples
4. **Develop**: Follow coding standards and testing guidelines

### **For AI Tools**
1. **Architecture**: Understand the [System Overview](architecture/system-overview.md)
2. **Patterns**: Learn the [Coding Standards](development/coding-standards.md)
3. **Integration**: Review [Service Communication](api/integration.md)
4. **Development**: Follow the [AI Tool Guide](development/ai-tool-guide.md)

## 📞 Support and Resources

### **Documentation Links**
- **API Documentation**: Available at `/docs` endpoint for each service
- **Database Schema**: [Complete schema documentation](database/schema.md)
- **Deployment Guide**: [Docker and AWS deployment](deployment/)

### **Development Resources**
- **Code Examples**: Available in each service's documentation
- **Test Suites**: Comprehensive test examples in `tests/` directories
- **Configuration Examples**: Environment templates in each service

---

This documentation provides a comprehensive guide to understanding, developing, and deploying the Minca AI Insurance Platform. It's specifically designed to help AI coding tools understand the project structure and make intelligent modifications.
