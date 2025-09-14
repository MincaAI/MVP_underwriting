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

from document_processor.services.extractor import DocumentExtractor
from document_processor.services.transformer import DocumentTransformer  
from document_processor.services.exporter import DocumentExporter
from document_processor.services.validator import DocumentValidator

app = FastAPI(
    title="Document Processor Service",
    description="Unified service for Excel document parsing, transformation, and generation",
    version="0.1.0"
)

# Initialize service components
extractor = DocumentExtractor()
transformer = DocumentTransformer()
exporter = DocumentExporter()
validator = DocumentValidator()

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
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: ProcessingRequest = ProcessingRequest(case_id="", profile="generic.yaml")
):
    """
    Extract data from uploaded Excel/CSV file
    """
    try:
        # Generate run ID if not provided
        run_id = request.run_id or str(uuid.uuid4())
        
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(status_code=400, detail="Only Excel and CSV files are supported")
        
        # Process file in background
        background_tasks.add_task(
            process_document_async,
            file, run_id, request.case_id, request.profile, request.export_template
        )
        
        return ProcessingResponse(
            run_id=run_id,
            case_id=request.case_id,
            status="processing",
            message="Document extraction started"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transform/{run_id}")
async def transform_document(
    run_id: str,
    profile: str = "generic.yaml",
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Transform extracted data using broker profile
    """
    try:
        # Add transformation task to background
        background_tasks.add_task(transform_document_async, run_id, profile)
        
        return ProcessingResponse(
            run_id=run_id,
            case_id="",  # Will be filled from database
            status="transforming", 
            message="Document transformation started"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/{run_id}")
async def export_document(
    run_id: str,
    template: str = "gcotiza_v1.yaml",
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Export transformed data to Excel format
    """
    try:
        # Add export task to background
        background_tasks.add_task(export_document_async, run_id, template)
        
        return ProcessingResponse(
            run_id=run_id,
            case_id="",  # Will be filled from database
            status="exporting",
            message="Document export started"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process", response_model=ProcessingResponse)
async def process_document_complete(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
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
        
        # Process complete pipeline in background
        background_tasks.add_task(
            process_complete_pipeline,
            file, run_id, case_id, profile, export_template
        )
        
        return ProcessingResponse(
            run_id=run_id,
            case_id=case_id,
            status="processing",
            message="Complete document processing started"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{run_id}")
async def get_processing_status(run_id: str):
    """
    Get processing status for a run
    """
    try:
        # This would query the database for run status
        # Placeholder for now
        return {
            "run_id": run_id,
            "status": "processing", 
            "progress": 50,
            "message": "Processing in progress"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def process_document_async(
    file: UploadFile, 
    run_id: str, 
    case_id: str, 
    profile: str,
    export_template: str
):
    """Process document extraction asynchronously"""
    try:
        # Extract data from file
        extracted_data = await extractor.extract(file, run_id, case_id)
        print(f"Extracted {len(extracted_data)} rows for run {run_id}")
        
    except Exception as e:
        print(f"Error in document extraction for run {run_id}: {e}")

async def transform_document_async(run_id: str, profile: str):
    """Transform document data asynchronously"""
    try:
        # Transform data using profile
        result = await transformer.transform(run_id, profile)
        print(f"Transformed data for run {run_id} using profile {profile}")
        
    except Exception as e:
        print(f"Error in document transformation for run {run_id}: {e}")

async def export_document_async(run_id: str, template: str):
    """Export document asynchronously"""
    try:
        # Export to Excel
        export_url = await exporter.export(run_id, template)
        print(f"Exported data for run {run_id} to {export_url}")
        
    except Exception as e:
        print(f"Error in document export for run {run_id}: {e}")

async def process_complete_pipeline(
    file: UploadFile,
    run_id: str,
    case_id: str, 
    profile: str,
    export_template: str
):
    """Process complete pipeline asynchronously"""
    try:
        # Step 1: Extract
        extracted_data = await extractor.extract(file, run_id, case_id)
        print(f"✓ Extracted {len(extracted_data)} rows")
        
        # Step 2: Transform  
        result = await transformer.transform(run_id, profile)
        print(f"✓ Transformed data using profile {profile}")
        
        # Step 3: Export
        export_url = await exporter.export(run_id, export_template)
        print(f"✓ Exported to {export_url}")
        
        print(f"🎉 Complete processing finished for run {run_id}")
        
    except Exception as e:
        print(f"❌ Error in complete pipeline for run {run_id}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)