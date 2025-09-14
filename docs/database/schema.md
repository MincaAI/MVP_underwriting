# Database Schema Documentation

This document provides comprehensive information about the PostgreSQL database schema for the Minca AI Insurance Platform.

## Schema Overview

The database is designed to support the complete insurance underwriting workflow, from email intake to case management and vehicle matching.

## Entity Relationship Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Messages     │    │      Cases      │    │    Vehicles     │
│                 │    │                 │    │                 │
│ • id (PK)       │    │ • id (PK)       │    │ • id (PK)       │
│ • provider_id   │    │ • message_id(FK)│    │ • case_id (FK)  │
│ • subject       │────│ • cot_number    │────│ • plate         │
│ • from_email    │    │ • client_name   │    │ • brand         │
│ • received_at   │    │ • client_rfc    │    │ • model         │
│ • status        │    │ • broker_name   │    │ • cvegs_code    │
│ • cot_number    │    │ • broker_email  │    │ • confidence    │
│ • confidence    │    │ • vehicle_count │    │ • warnings      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       
         │              ┌─────────────────┐              
         │              │    Coverages    │              
         │              │                 │              
         │              │ • id (PK)       │              
         │              │ • case_id (FK)  │              
         │              │ • unit_type     │              
         │              │ • coverage      │              
         │              │ • limit         │              
         │              │ • deductible    │              
         │              └─────────────────┘              
         │                                               
┌─────────────────┐              ┌─────────────────┐    
│   Attachments   │              │  COT Sequences  │    
│                 │              │                 │    
│ • id (PK)       │              │ • year (PK)     │    
│ • message_id(FK)│──────────────│ • next_sequence │    
│ • name          │              │ • created_at    │    
│ • mime_type     │              │ • updated_at    │    
│ • storage_path  │              └─────────────────┘    
│ • sha256        │                                     
│ • is_processed  │                                     
└─────────────────┘                                     
```

## Table Definitions

### **messages**
Stores email messages received from Outlook with processing metadata.

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(255) UNIQUE NOT NULL,  -- Microsoft Graph message ID
    subject TEXT,
    from_name VARCHAR(255),
    from_email VARCHAR(255),
    received_at TIMESTAMP WITH TIME ZONE,
    folder VARCHAR(100),
    status message_status DEFAULT 'NEW' NOT NULL,
    cot_number VARCHAR(50) UNIQUE,
    confidence NUMERIC(3,2),                   -- Overall confidence (0.00-1.00)
    missing TEXT[],                            -- Array of missing fields
    raw_body_path VARCHAR(500),                -- Path to stored email body
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_messages_provider_id ON messages(provider_id);
CREATE INDEX idx_messages_from_email ON messages(from_email);
CREATE INDEX idx_messages_received_at ON messages(received_at);
CREATE INDEX idx_messages_status ON messages(status);
CREATE INDEX idx_messages_cot_number ON messages(cot_number);

-- Enum for message status
CREATE TYPE message_status AS ENUM (
    'NEW', 'PROCESSING', 'PROCESSED', 'NEEDS_REVIEW', 'ERROR'
);
```

### **cases**
Represents insurance cases extracted from email messages.

```sql
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    cot_number VARCHAR(50) UNIQUE NOT NULL,    -- TK-YYYY-NNN format
    client_name VARCHAR(255),
    client_rfc VARCHAR(20),                    -- RFC (Mexican tax ID)
    broker_name VARCHAR(255),
    broker_email VARCHAR(255),
    vehicle_count INTEGER DEFAULT 0,
    loss_history TEXT,
    policy_type VARCHAR(100),
    effective_date TIMESTAMP WITH TIME ZONE,
    expiration_date TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_cases_message_id ON cases(message_id);
CREATE INDEX idx_cases_cot_number ON cases(cot_number);
CREATE INDEX idx_cases_client_name ON cases(client_name);
CREATE INDEX idx_cases_client_rfc ON cases(client_rfc);
CREATE INDEX idx_cases_broker_email ON cases(broker_email);
```

### **vehicles**
Stores vehicle information with CVEGS matching results.

```sql
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    
    -- Vehicle identification
    plate VARCHAR(20),
    vin VARCHAR(17),
    
    -- Vehicle details
    brand VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    value NUMERIC(12,2),                       -- Vehicle value
    usage VARCHAR(100),                        -- Usage type
    unit_type VARCHAR(100),                    -- TRACTO, REMOLQUE, etc.
    description TEXT,                          -- Full description
    mod VARCHAR(100),                          -- Modifications
    claims_history BOOLEAN DEFAULT FALSE,
    
    -- CVEGS matching results
    cvegs_code VARCHAR(20),                    -- Matched CVEGS code
    cvegs_confidence NUMERIC(3,2),             -- Confidence (0.00-1.00)
    cvegs_matched_description TEXT,            -- Description from dataset
    cvegs_match_method VARCHAR(50),            -- Matching method used
    
    -- Processing metadata
    original_description TEXT,                 -- Original input description
    extracted_attributes TEXT,                 -- JSON of extracted attributes
    processing_warnings TEXT,                  -- JSON array of warnings
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vehicles_case_id ON vehicles(case_id);
CREATE INDEX idx_vehicles_plate ON vehicles(plate);
CREATE INDEX idx_vehicles_vin ON vehicles(vin);
CREATE INDEX idx_vehicles_brand ON vehicles(brand);
CREATE INDEX idx_vehicles_model ON vehicles(model);
CREATE INDEX idx_vehicles_year ON vehicles(year);
CREATE INDEX idx_vehicles_cvegs_code ON vehicles(cvegs_code);
```

### **coverages**
Insurance coverage information extracted from documents.

```sql
CREATE TABLE coverages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    unit_type VARCHAR(100),                    -- Type of unit covered
    coverage VARCHAR(255) NOT NULL,           -- Coverage type/name
    limit VARCHAR(100),                       -- Coverage limit
    deductible VARCHAR(100),                  -- Deductible amount
    status VARCHAR(50),                       -- Coverage status
    premium VARCHAR(100),                     -- Premium amount
    currency VARCHAR(10) DEFAULT 'MXN',       -- Currency code
    description TEXT,                         -- Detailed description
    exclusions TEXT,                          -- Coverage exclusions
    conditions TEXT,                          -- Special conditions
    extracted_from VARCHAR(100),              -- Source of extraction
    confidence VARCHAR(20),                   -- Extraction confidence
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_coverages_case_id ON coverages(case_id);
```

### **attachments**
File attachments from email messages.

```sql
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- File information
    name VARCHAR(255) NOT NULL,               -- Original filename
    mime_type VARCHAR(100),                   -- MIME type
    size_bytes INTEGER,                       -- File size
    storage_path VARCHAR(500) NOT NULL,       -- Storage location
    sha256 VARCHAR(64),                       -- File hash
    
    -- Processing metadata
    is_processed VARCHAR(20) DEFAULT 'pending', -- pending/processed/failed
    processing_notes TEXT,                    -- Processing notes/errors
    content_type VARCHAR(50),                 -- Document type
    page_count INTEGER,                       -- Pages (for PDFs)
    sheet_count INTEGER,                      -- Sheets (for Excel)
    
    -- Extraction results
    extracted_text TEXT,                      -- Extracted text content
    extracted_tables TEXT,                    -- JSON of extracted tables
    vehicle_data_found VARCHAR(20) DEFAULT 'unknown', -- yes/no/unknown
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_attachments_message_id ON attachments(message_id);
CREATE INDEX idx_attachments_sha256 ON attachments(sha256);
```

### **cot_sequences**
Manages COT number generation with year-based sequencing.

```sql
CREATE TABLE cot_sequences (
    year INTEGER PRIMARY KEY,                 -- Year (e.g., 2024)
    next_sequence INTEGER NOT NULL DEFAULT 1, -- Next sequence number
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Data Types and Constraints

### **UUID Primary Keys**
All tables use UUID primary keys for:
- **Global Uniqueness**: UUIDs are globally unique across systems
- **Security**: Non-sequential IDs prevent enumeration attacks
- **Distribution**: UUIDs work well in distributed systems
- **Integration**: Easy integration with external systems

### **Timestamp Handling**
All timestamps use `TIMESTAMP WITH TIME ZONE` for:
- **Global Consistency**: Proper timezone handling
- **Audit Trails**: Accurate creation and modification tracking
- **Reporting**: Consistent time-based queries

### **JSON Storage**
Complex data is stored as TEXT (JSON strings) for:
- **Flexibility**: Schema-less storage for variable data
- **Performance**: Avoid complex joins for nested data
- **Compatibility**: Works with all PostgreSQL versions

## Business Rules

### **COT Number Generation**
- **Format**: `TK-YYYY-NNN` (e.g., `TK-2024-001`)
- **Uniqueness**: Sequential per year, globally unique
- **Reset**: Sequence resets each year starting from 001
- **Concurrency**: Thread-safe generation using database locks

### **Message Processing Status**
- **NEW**: Message received, not yet processed
- **PROCESSING**: Currently being processed
- **PROCESSED**: Successfully processed
- **NEEDS_REVIEW**: Requires manual review
- **ERROR**: Processing failed

### **Vehicle Confidence Levels**
- **High**: Confidence ≥ 0.9 (automatic processing)
- **Medium**: Confidence 0.7-0.89 (review recommended)
- **Low**: Confidence 0.5-0.69 (manual review required)
- **Very Low**: Confidence < 0.5 (manual intervention required)

## Data Relationships

### **One-to-One Relationships**
- **Message ↔ Case**: Each message creates one case
- **Case → COT Number**: Each case has a unique COT number

### **One-to-Many Relationships**
- **Message → Attachments**: One message can have multiple attachments
- **Case → Vehicles**: One case can have multiple vehicles
- **Case → Coverages**: One case can have multiple coverage types

### **Foreign Key Constraints**
- **Cascade Deletes**: Deleting a case removes all associated vehicles and coverages
- **Referential Integrity**: All foreign keys are enforced
- **Orphan Prevention**: Cannot create vehicles without a valid case

## Performance Considerations

### **Indexing Strategy**
- **Primary Keys**: Automatic B-tree indexes on all primary keys
- **Foreign Keys**: Indexes on all foreign key columns
- **Search Fields**: Indexes on frequently searched columns (email, plate, COT)
- **Composite Indexes**: Multi-column indexes for complex queries

### **Query Optimization**
- **Selective Loading**: Use `selectinload` for relationships
- **Pagination**: Limit and offset for large result sets
- **Filtering**: Early filtering to reduce data transfer
- **Caching**: Redis caching for frequently accessed data

### **Connection Management**
- **Connection Pooling**: SQLAlchemy connection pool with configurable size
- **Async Operations**: All database operations are asynchronous
- **Transaction Management**: Proper transaction boundaries and rollback handling

## Migration Strategy

### **Alembic Configuration**
- **Auto-generation**: Automatic migration generation from model changes
- **Version Control**: All migrations tracked in version control
- **Rollback Support**: All migrations include downgrade procedures
- **Environment Isolation**: Separate migration tracking per environment

### **Migration Best Practices**
- **Backward Compatibility**: New migrations don't break existing code
- **Data Preservation**: Migrations preserve existing data
- **Performance**: Large table migrations use batching
- **Testing**: All migrations tested in staging before production

## Data Validation

### **Model-Level Validation**
- **Pydantic Integration**: SQLAlchemy models work with Pydantic validation
- **Type Safety**: Strong typing with Python type hints
- **Constraint Enforcement**: Database constraints for data integrity
- **Business Rules**: Model properties for business logic validation

### **Application-Level Validation**
- **Input Validation**: API requests validated with Pydantic models
- **Business Logic**: Repository methods enforce business rules
- **Data Consistency**: Cross-table validation in service layer
- **Error Handling**: Comprehensive validation error messages

## Security Considerations

### **Data Protection**
- **Encryption at Rest**: Database encryption enabled
- **Encryption in Transit**: TLS for all database connections
- **Access Control**: Role-based database access
- **Audit Logging**: All data changes logged

### **PII Handling**
- **Data Minimization**: Only store necessary personal information
- **Anonymization**: Option to anonymize data for analytics
- **Retention Policies**: Automated data retention and deletion
- **Compliance**: GDPR and insurance industry compliance

## Backup and Recovery

### **Backup Strategy**
- **Automated Backups**: Daily full backups with point-in-time recovery
- **Cross-Region Replication**: Backups replicated to multiple regions
- **Retention Policy**: 30-day backup retention with yearly archives
- **Testing**: Regular backup restoration testing

### **Recovery Procedures**
- **Point-in-Time Recovery**: Restore to any point within retention period
- **Partial Recovery**: Restore specific tables or data ranges
- **Disaster Recovery**: Complete system recovery procedures
- **Data Validation**: Post-recovery data integrity checks

## Monitoring and Maintenance

### **Performance Monitoring**
- **Query Performance**: Slow query logging and analysis
- **Index Usage**: Monitor index effectiveness and usage
- **Connection Monitoring**: Track connection pool utilization
- **Resource Usage**: Monitor CPU, memory, and disk usage

### **Maintenance Tasks**
- **Index Maintenance**: Regular index rebuilding and optimization
- **Statistics Updates**: Keep query planner statistics current
- **Vacuum Operations**: Regular table maintenance for performance
- **Log Rotation**: Automated log file management

## Development Guidelines

### **Schema Changes**
1. **Create Migration**: Use Alembic to generate migration
2. **Review Migration**: Manually review generated SQL
3. **Test Migration**: Test in development environment
4. **Deploy Migration**: Apply to staging, then production

### **Query Patterns**
```python
# Efficient relationship loading
case = await session.execute(
    select(Case)
    .options(selectinload(Case.vehicles))
    .where(Case.id == case_id)
)

# Proper pagination
vehicles = await session.execute(
    select(Vehicle)
    .where(Vehicle.case_id == case_id)
    .order_by(Vehicle.created_at)
    .limit(50)
    .offset(page * 50)
)

# Efficient counting
count = await session.execute(
    select(func.count(Vehicle.id))
    .where(Vehicle.cvegs_confidence >= 0.9)
)
```

### **Repository Usage**
```python
# Use repositories for data access
case_repo = CaseRepository(db)
vehicle_repo = VehicleRepository(db)

# Create case with COT
case = await case_repo.create_case_with_cot(
    client_name="Example Client",
    broker_email="broker@example.com"
)

# Create vehicle with CVEGS results
vehicle = await vehicle_repo.create_vehicle_with_cvegs(
    case_id=case.id,
    vehicle_data={"plate": "ABC123", "brand": "TOYOTA"},
    cvegs_result={"cvegs_code": "12345", "confidence_score": 0.95}
)
```

This schema provides a robust foundation for the insurance underwriting platform with proper relationships, constraints, and performance optimizations.
