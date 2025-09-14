import sys
import pathlib
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "schemas" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "storage" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "mq" / "src"))

from app.db.session import engine
from app.db.models import Run, Component, RunStatus
from app.storage.s3 import upload_bytes
from app.mq.queue_factory import QueueFactory

app = FastAPI(
    title="Document Processor Service",
    description="Queue-based document processing service for Excel parsing, transformation, and generation",
    version="0.2.0"
)

class ProcessingRequest(BaseModel):
    case_id: str
    run_id: Optional[str] = None
    profile: str = "generic.yaml"
    export_template: str = "gcotiza_v1.yaml"

class ProcessingResponse(BaseModel):
    run_id: str
    case_id: str
    status: str
    message: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "document-processor"}

@app.post("/extract", response_model=ProcessingResponse)
async def extract_document(
    file: UploadFile = File(...),
    case_id: str = "",
    profile: str = "generic.yaml",
    export_template: str = "gcotiza_v1.yaml"
):
    """
    Extract data from uploaded Excel/CSV file using queue-based processing
    """
    try:
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(status_code=400, detail="Only Excel and CSV files are supported")
        
        # Upload file to S3
        file_content = await file.read()
        s3_key = f"uploads/{run_id}/{file.filename}"
        bucket = "mvp-underwriting-uploads"  # Default bucket
        s3_uri = upload_bytes(bucket, s3_key, file_content)
        
        # Create database run record
        await _create_run_record(run_id, case_id, Component.EXTRACT, file.filename)
        
        # Publish EXTRACT message to queue
        extract_message = {
            "msg_id": str(uuid.uuid4()),
            "case_id": case_id,
            "run_id": run_id,
            "component": "EXTRACT",
            "payload": {
                "s3_uri": s3_uri,
                "profile": profile,
                "export_template": export_template
            }
        }
        
        await QueueFactory.get_publisher().send_message("mvp-underwriting-extract", extract_message)
        
        return ProcessingResponse(
            run_id=run_id,
            case_id=case_id,
            status="queued",
            message="Document extraction queued for processing"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transform/{run_id}")
async def transform_document(
    run_id: str,
    profile: str = "generic.yaml",
    export_template: str = "gcotiza_v1.yaml"
):
    """
    Transform extracted data using broker profile
    """
    try:
        # Get case_id from database
        case_id = await _get_case_id_from_run(run_id)
        
        # Publish TRANSFORM message to queue
        transform_message = {
            "msg_id": str(uuid.uuid4()),
            "case_id": case_id,
            "run_id": run_id,
            "component": "TRANSFORM",
            "payload": {
                "profile": profile,
                "export_template": export_template
            }
        }
        
        await QueueFactory.get_publisher().send_message("mvp-underwriting-transform", transform_message)
        
        return ProcessingResponse(
            run_id=run_id,
            case_id=case_id,
            status="queued", 
            message="Document transformation queued for processing"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/{run_id}")
async def export_document(
    run_id: str,
    template: str = "gcotiza_v1.yaml"
):
    """
    Export transformed data to Excel format
    """
    try:
        # Get case_id from database
        case_id = await _get_case_id_from_run(run_id)
        
        # Publish EXPORT message to queue
        export_message = {
            "msg_id": str(uuid.uuid4()),
            "case_id": case_id,
            "run_id": run_id,
            "component": "EXPORT",
            "payload": {
                "template": template
            }
        }
        
        await QueueFactory.get_publisher().send_message("mvp-underwriting-export", export_message)
        
        return ProcessingResponse(
            run_id=run_id,
            case_id=case_id,
            status="queued",
            message="Document export queued for processing"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process", response_model=ProcessingResponse)
async def process_document_complete(
    file: UploadFile = File(...),
    case_id: str = "",
    profile: str = "generic.yaml",
    export_template: str = "gcotiza_v1.yaml"
):
    """
    Complete document processing pipeline: extract -> transform -> export
    """
    try:
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(status_code=400, detail="Only Excel and CSV files are supported")
        
        # Upload file to S3
        file_content = await file.read()
        s3_key = f"uploads/{run_id}/{file.filename}"
        bucket = "mvp-underwriting-uploads"  # Default bucket
        s3_uri = upload_bytes(bucket, s3_key, file_content)
        
        # Create database run record
        await _create_run_record(run_id, case_id, Component.EXTRACT, file.filename)
        
        # Publish EXTRACT message to queue (pipeline will continue automatically)
        extract_message = {
            "msg_id": str(uuid.uuid4()),
            "case_id": case_id,
            "run_id": run_id,
            "component": "EXTRACT",
            "payload": {
                "s3_uri": s3_uri,
                "profile": profile,
                "export_template": export_template
            }
        }
        
        await QueueFactory.get_publisher().send_message("mvp-underwriting-extract", extract_message)
        
        return ProcessingResponse(
            run_id=run_id,
            case_id=case_id,
            status="queued",
            message="Complete document processing pipeline queued"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{run_id}")
async def get_processing_status(run_id: str):
    """
    Get detailed processing status for a run including all pipeline stages
    """
    try:
        from sqlalchemy.orm import Session
        
        with Session(engine) as session:
            # Get main run
            main_run = session.get(Run, run_id)
            if not main_run:
                raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
            
            # Get all related runs (transform, export)
            all_runs = session.query(Run).filter(
                (Run.id == run_id) | 
                (Run.id == f"{run_id}_transform") | 
                (Run.id == f"{run_id}_export")
            ).all()
            
            # Build status response
            status_info = {
                "run_id": run_id,
                "case_id": main_run.case_id,
                "overall_status": _determine_overall_status(all_runs),
                "progress": _calculate_progress(all_runs),
                "stages": {},
                "created_at": main_run.started_at.isoformat() if main_run.started_at else None,
                "file_name": main_run.file_name
            }
            
            # Add stage-specific information
            for run in all_runs:
                stage_name = _get_stage_name(run.id, run_id)
                status_info["stages"][stage_name] = {
                    "status": run.status.value if run.status else "unknown",
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "metrics": run.metrics or {},
                    "error_message": run.error_message
                }
            
            return status_info
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _determine_overall_status(runs: list) -> str:
    """Determine overall pipeline status from individual run statuses"""
    if not runs:
        return "unknown"
    
    statuses = [run.status for run in runs if run.status]
    
    if any(status == RunStatus.FAILED for status in statuses):
        return "failed"
    elif any(status == RunStatus.ERROR for status in statuses):
        return "error"
    elif all(status == RunStatus.SUCCESS for status in statuses):
        return "completed"
    elif any(status in [RunStatus.STARTED, RunStatus.PROCESSING] for status in statuses):
        return "processing"
    elif any(status == RunStatus.QUEUED for status in statuses):
        return "queued"
    else:
        return "unknown"

def _calculate_progress(runs: list) -> int:
    """Calculate overall progress percentage"""
    if not runs:
        return 0
    
    # Define stage weights
    stage_weights = {"extract": 30, "transform": 40, "export": 30}
    total_progress = 0
    
    for run in runs:
        stage_name = _get_stage_name(run.id, runs[0].id.split('_')[0])
        weight = stage_weights.get(stage_name, 0)
        
        if run.status == RunStatus.SUCCESS:
            total_progress += weight
        elif run.status in [RunStatus.STARTED, RunStatus.PROCESSING]:
            total_progress += weight * 0.5  # 50% for in-progress
        # Queued or failed stages contribute 0
    
    return min(100, total_progress)

def _get_stage_name(run_id: str, base_run_id: str) -> str:
    """Get stage name from run ID"""
    if run_id == base_run_id:
        return "extract"
    elif run_id == f"{base_run_id}_transform":
        return "transform"
    elif run_id == f"{base_run_id}_export":
        return "export"
    else:
        return "unknown"

# Helper functions
async def _create_run_record(run_id: str, case_id: str, component: Component, filename: str):
    """Create a new run record in the database"""
    from sqlalchemy.orm import Session
    from datetime import datetime
    
    with Session(engine) as session:
        run = Run(
            id=run_id,
            case_id=case_id,
            component=component,
            status=RunStatus.QUEUED,
            file_name=filename,
            started_at=datetime.utcnow()
        )
        session.add(run)
        session.commit()

async def _get_case_id_from_run(run_id: str) -> str:
    """Get case_id from existing run record"""
    from sqlalchemy.orm import Session
    
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return run.case_id

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
