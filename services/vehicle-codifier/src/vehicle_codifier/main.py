"""Simplified FastAPI application for vehicle codification."""

import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import sys
import pathlib

from .config import get_settings
from .models import (
    VehicleInput, FlexibleMatchRequest, FlexibleMatchResponse, HealthResponse
)
from .core import VehicleCodeifier
from .pipeline import VehiclePreprocessor

# Add packages to path for database access (optional - commented out for simplified service)
# sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))
# from app.db.session import engine
# from app.db.models import Run, Row, Codify, Component, RunStatus
# from sqlalchemy.orm import Session

# Database dependencies - only import if available
try:
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))
    from app.db.session import engine
    from app.db.models import Run, Row, Codify, Component, RunStatus
    from sqlalchemy.orm import Session
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️  Database modules not available - batch processing endpoint disabled")

# Initialize settings and services
settings = get_settings()
codifier = VehicleCodeifier()
preprocessor = VehiclePreprocessor()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Simplified vehicle description to CVEGS code matching using pgvector similarity"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    health_status = codifier.get_health_status()

    return HealthResponse(
        status=health_status["status"],
        version=settings.app_version,
        database_connected=health_status["database_connected"],
        active_catalog_version=health_status.get("active_catalog_version"),
        catalog_records=health_status.get("catalog_records", 0),
        embedding_model=health_status["embedding_model"]
    )


@app.post("/match", response_model=FlexibleMatchResponse)
async def match_vehicles(request: FlexibleMatchRequest):
    """
    Match vehicles against the CATVER catalog with flexible JSON format.

    Handles numbered JSON objects with flexible field names:
    {
        "0": {"modelo": 2020, "description": "toyota yaris sol l"},
        "1": {"año": 2019, "descripcion": "honda civic ex"},
        "2": {"year": 2021, "desc": "nissan sentra advance"}
    }
    """
    start_time = time.time()

    results = {}
    field_mappings = {}
    errors = {}

    # Use unified processing method
    try:
        # Process all inputs at once using the unified preprocessor
        processed_batch = preprocessor.process(request.root)

        # Process each successfully preprocessed row
        for row_id, processed_row in processed_batch.items():
            try:
                # Create VehicleInput and match
                vehicle_input = VehicleInput(
                    modelo=processed_row["model_year"],
                    description=processed_row["description"]
                )
                result = codifier.match_vehicle(vehicle_input)
                results[row_id] = result

            except Exception as e:
                errors[row_id] = f"Matching failed: {str(e)}"

        # Track rows that failed preprocessing
        for row_id in request.root.keys():
            if row_id not in processed_batch and row_id not in errors:
                errors[row_id] = "Failed to detect year and description fields"

    except Exception as e:
        # Handle preprocessing errors
        print(f"Unified preprocessing failed: {e}")
        for row_id in request.root.keys():
            errors[row_id] = f"Preprocessing failed: {str(e)}"

    successful_matches = sum(1 for r in results.values() if r.success)
    processing_time_ms = (time.time() - start_time) * 1000

    return FlexibleMatchResponse(
        results=results,
        total_processed=len(request.root),
        successful_matches=successful_matches,
        processing_time_ms=processing_time_ms,
        field_mappings=field_mappings,
        errors=errors
    )


@app.get("/metrics")
async def get_metrics():
    """Get service metrics and configuration."""
    health_status = codifier.get_health_status()

    return {
        "service_info": {
            "name": settings.app_name,
            "version": settings.app_version,
            "architecture": "Simplified Service (5 files)",
            "embedding_model": settings.embedding_model,
            "embedding_dimension": settings.embedding_dimension
        },
        "database": {
            "connected": health_status["database_connected"],
            "active_catalog": health_status.get("active_catalog_version"),
            "records": health_status.get("catalog_records", 0)
        },
        "matching_config": {
            "threshold_high": settings.threshold_high,
            "threshold_low": settings.threshold_low,
            "weight_embedding": settings.weight_embedding,
            "weight_fuzzy": settings.weight_fuzzy,
            "max_candidates": settings.max_candidates,
            "max_results": settings.max_results
        },
        "capabilities": {
            "embedding_similarity": health_status.get("embedder_available", False),
            "llm_extraction": bool(settings.openai_api_key),
            "pgvector_search": True,
            "hybrid_scoring": True
        }
    }


@app.post("/codify/batch")
async def codify_batch(run_id: Optional[str] = None, case_id: Optional[str] = None):
    """
    Database-driven batch codification - compatible with main API.

    Args:
        run_id: Optional existing run ID to process
        case_id: Optional case ID for new runs

    Returns:
        Run results with metrics
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database modules not available - batch processing disabled"
        )

    start_time = time.time()

    with Session(engine) as session:
        if not run_id:
            run_id = str(uuid.uuid4())
            session.add(Run(
                id=run_id,
                case_id=case_id,
                component=Component.CODIFY,
                status=RunStatus.STARTED
            ))
            session.commit()

        # Get all rows for this run
        rows = session.query(Row).filter(
            Row.run_id == run_id,
            Row.transformed_data.isnot(None)
        ).all()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No transformed data found for run {run_id}")

        # Process each row
        results = []
        for row in rows:
            try:
                # Extract modelo and description from transformed data
                transformed = row.transformed_data
                modelo = transformed.get("year") or transformed.get("modelo") or transformed.get("model_year")
                description = transformed.get("description") or transformed.get("desc") or ""

                if not modelo or not description:
                    # Skip rows without required data
                    continue

                # Create VehicleInput for our codifier
                vehicle_input = VehicleInput(modelo=int(modelo), description=str(description))

                # Match using our simplified codifier
                match_result = codifier.match_vehicle(vehicle_input)

                # Store result in Codify table
                codify_result = Codify(
                    run_id=run_id,
                    row_idx=row.row_index,
                    suggested_cvegs=str(match_result.suggested_cvegs) if match_result.suggested_cvegs else None,
                    confidence=match_result.confidence,
                    candidates=[{
                        "cvegs": str(c.cvegs),
                        "score": c.final_score,
                        "label": c.label
                    } for c in match_result.candidates],
                    decision=match_result.decision
                )
                session.add(codify_result)
                results.append(match_result)

            except Exception:
                # Store failed result
                codify_result = Codify(
                    run_id=run_id,
                    row_idx=row.row_index,
                    suggested_cvegs=None,
                    confidence=0.0,
                    candidates=[],
                    decision="no_match"
                )
                session.add(codify_result)

        # Update run status and metrics
        run = session.get(Run, run_id)
        if run:
            run.status = RunStatus.SUCCESS
            run.finished_at = time.time()

            # Calculate metrics
            successful_matches = sum(1 for r in results if r.success)
            run.metrics = {
                "total_rows": len(rows),
                "processed_rows": len(results),
                "successful_matches": successful_matches,
                "auto_accept": sum(1 for r in results if r.decision == "auto_accept"),
                "needs_review": sum(1 for r in results if r.decision == "needs_review"),
                "no_match": sum(1 for r in results if r.decision == "no_match"),
                "processing_time_ms": (time.time() - start_time) * 1000,
                "confidence_avg": sum(r.confidence for r in results) / len(results) if results else 0
            }

        session.commit()

        return {"run_id": run_id, "metrics": run.metrics}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.debug
    )