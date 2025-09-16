import uuid
import time
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .config.settings import get_settings
from .models.vehicle import (
    MatchResult,
    BatchMatchRequest,
    BatchMatchResponse,
    HealthResponse
)
from .models.response import SuccessResponse, ErrorResponse, ValidationErrorResponse
from .services.batch_processor import BatchProcessor
from .services.matcher import CVEGSMatcher
from .services.data_loader import DataLoader

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global instances - legacy services
batch_processor = BatchProcessor()
matcher = CVEGSMatcher()
data_loader = DataLoader()
settings = get_settings()

# Clean architecture controller
from .presentation.controllers.vehicle_matching_controller import VehicleMatchingController
from .infrastructure.di_container import get_container

# Initialize clean architecture
clean_controller = VehicleMatchingController()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with clean architecture initialization."""
    # Startup
    logger.info("Starting Vehicle CVEGS Matcher service with Clean Architecture", 
               version=settings.app_version)
    
    try:
        # Initialize legacy services for backward compatibility
        await matcher.initialize_insurer("default")
        
        # Warm up clean architecture services
        container = get_container()
        container.warm_up()
        
        logger.info("Service initialized successfully with Clean Architecture enabled")
    except FileNotFoundError as e:
        # Dataset file missing - continue startup so health/docs are available
        logger.error("Dataset file not found during initialization", error=str(e))
        logger.warning(
            "Continuing startup without dataset. Load catalog data via S3 → Postgres first, then POST /insurers/{insurer_id}/initialize"
        )
    except Exception as e:
        logger.error("Failed to initialize service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Vehicle CVEGS Matcher service")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="High-accuracy vehicle description to CVEGS code matching service",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add to structured logging context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error("Unhandled exception", error=str(exc), exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            error_code="INTERNAL_ERROR",
            request_id=getattr(request.state, 'request_id', None),
            error_details={"error": str(exc)} if settings.debug else None
        ).dict()
    )


# Health check endpoint - Clean Architecture Enhanced
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Enhanced health check endpoint using Clean Architecture."""
    try:
        # Get health status from clean architecture services
        health_status = await clean_controller.get_health_status()
        
        # Legacy compatibility checks
        openai_available = bool(settings.openai_api_key)
        redis_available = True  # Implement actual Redis health check
        
        return HealthResponse(
            status=health_status.get('status', 'healthy'),
            timestamp=health_status.get('timestamp', datetime.utcnow()),
            version=settings.app_version,
            dataset_loaded=health_status.get('dataset_loaded', False),
            dataset_records=health_status.get('dataset_records', 0),
            openai_available=openai_available,
            redis_available=redis_available
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")


"""Batch-only vehicle matching endpoint - Clean Architecture"""
@app.post("/match", response_model=BatchMatchResponse, tags=["Matching"])
async def match_vehicles(
    request_data: BatchMatchRequest,
    request: Request
):
    """
    Batch vehicle matching.

    Request body (BatchMatchRequest):
    {
        "vehicles": [
            {
                "description": "TOYOTA YARIS SOL L 2020",
                "brand": "TOYOTA",
                "model": "YARIS",
                "year": 2020
            }
        ],
        "insurer_id": "default",
        "parallel_processing": true
    }
    """
    # Validate batch request
    validation_errors = clean_controller.validate_batch_request(request_data)
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {'; '.join(validation_errors)}"
        )

    return await clean_controller.match_batch_vehicles(request_data)

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid request format. Expected VehicleInput or BatchMatchRequest."
        )


# Dataset statistics endpoint
@app.get("/datasets/stats", tags=["Datasets"])
async def get_dataset_stats():
    """Get statistics about loaded datasets."""
    try:
        stats = data_loader.get_stats()
        
        return SuccessResponse(
            message="Dataset statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.error("Failed to get dataset stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve dataset statistics")


# Initialize insurer endpoint
@app.post("/insurers/{insurer_id}/initialize", tags=["Insurers"])
async def initialize_insurer(insurer_id: str):
    """Initialize data for a specific insurer."""
    try:
        logger.info("Initializing insurer", insurer_id=insurer_id)
        
        await matcher.initialize_insurer(insurer_id)
        
        # Get stats for the initialized insurer
        stats = data_loader.get_stats().get(insurer_id, {})
        
        return SuccessResponse(
            message=f"Insurer {insurer_id} initialized successfully",
            data={
                "insurer_id": insurer_id,
                "records": stats.get("records", 0),
                "brands": stats.get("brands", 0),
                "models": stats.get("models", 0)
            }
        )
        
    except Exception as e:
        logger.error("Failed to initialize insurer", 
                    insurer_id=insurer_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initialize insurer {insurer_id}: {str(e)}"
        )


# Batch processing statistics endpoint
@app.get("/batch/stats", tags=["Batch Processing"])
async def get_batch_stats():
    """Get batch processing statistics and configuration."""
    try:
        stats = await batch_processor.get_batch_stats()
        
        return SuccessResponse(
            message="Batch statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.error("Failed to get batch stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve batch statistics")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# Worker-style batch codification endpoint
@app.post("/codify/batch", tags=["Codification"])
async def codify_batch(run_id: Optional[str] = None, case_id: Optional[str] = None):
    """
    Run codification batch processing.
    
    Args:
        run_id: Optional existing run ID to process
        case_id: Optional case ID for new runs
        
    Returns:
        Run results with metrics
    """
    # Import worker functions
    from .worker.main import process_run
    from sqlalchemy.orm import Session
    import sys
    import pathlib
    
    # Add packages to path
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))
    
    from app.db.session import engine
    from app.db.models import Run, Component, RunStatus
    
    with Session(engine) as s:
        if not run_id:
            run_id = str(uuid.uuid4())
            s.add(Run(
                id=run_id, 
                case_id=case_id, 
                component=Component.CODIFY, 
                status=RunStatus.STARTED
            ))
            s.commit()
        
        # Process the run synchronously for MVP
        process_run(run_id)
        
        # Get updated run with metrics
        run = s.get(Run, run_id)
        return {"run_id": run_id, "metrics": run.metrics}


# Enhanced metrics endpoint with Clean Architecture
@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Get comprehensive service metrics using Clean Architecture."""
    try:
        # Get metrics from clean architecture controller
        clean_metrics = await clean_controller.get_service_metrics()
        
        # Legacy metrics for backward compatibility
        dataset_stats = data_loader.get_stats()
        batch_stats = await batch_processor.get_batch_stats()
        
        return {
            "service_info": {
                "name": settings.app_name,
                "version": settings.app_version,
                "architecture": "Clean Architecture with Domain-Driven Design",
                "uptime": "N/A",  # Would implement actual uptime tracking
                "features": clean_metrics.get('matching_features', {})
            },
            "clean_architecture": clean_metrics.get('clean_architecture', {}),
            "dataset_stats": dataset_stats,
            "batch_config": batch_stats,
            "repository_metrics": clean_metrics.get('dataset_metrics', {}),
            "performance_optimizations": clean_metrics.get('performance_optimizations', {}),
            "system_config": {
                "max_batch_size": settings.max_batch_size,
                "max_concurrent_requests": settings.max_concurrent_requests,
                "confidence_threshold": settings.confidence_threshold,
                "chunk_size": 50,
                "supported_excel_columns": [
                    "Paquete De Cobert", "Marca", "Submarka", 
                    "Descripcion", "SERIE", "Ano MOdelos"
                ],
                "clean_architecture_layers": [
                    "Domain (Entities, Value Objects, Services)",
                    "Application (Use Cases)",
                    "Infrastructure (Repositories, Adapters)",
                    "Presentation (Controllers)"
                ]
            }
        }
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
