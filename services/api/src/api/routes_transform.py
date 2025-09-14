from fastapi import APIRouter
from sqlalchemy.orm import Session
import uuid
import sys
import pathlib

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))

from app.db.session import engine
from app.db.models import Run, Component, RunStatus

# Add worker-transform to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent / "worker-transform" / "src"))

from worker_transform.main import process_transform

router = APIRouter(prefix="/transform")

@router.post("")
def transform(case_id: str, s3_uri: str, profile: str = "configs/broker-profiles/lucky_gas.yaml"):
    """
    Transform broker data using a profile.
    
    Args:
        case_id: Case identifier
        s3_uri: S3 URI of the source file
        profile: Path to broker profile YAML
        
    Returns:
        Transform run information
    """
    run_id = str(uuid.uuid4())
    
    with Session(engine) as s:
        s.add(Run(
            id=run_id, 
            case_id=case_id, 
            component=Component.TRANSFORM, 
            status=RunStatus.STARTED
        ))
        s.commit()
    
    # Process transformation synchronously for MVP
    process_transform(run_id, s3_uri, profile)
    
    return {"run_id": run_id}

@router.get("/preview")
def preview(run_id: str, limit: int = 10):
    """
    Get preview of transformed data.
    
    Args:
        run_id: Transform run ID
        limit: Number of rows to preview
        
    Returns:
        Preview data with first N transformed rows
    """
    with Session(engine) as s:
        run = s.get(Run, run_id)
        if not run or run.component != Component.TRANSFORM:
            return {"error": "Transform run not found"}
        
        # Get first N rows
        from app.db.models import Row
        rows = (
            s.query(Row)
             .filter(Row.run_id == run_id)
             .order_by(Row.row_idx)
             .limit(limit)
             .all()
        )
        
        preview_data = []
        for row in rows:
            preview_data.append({
                "row_idx": row.row_idx,
                "transformed": row.transformed,
                "errors": row.errors,
                "warnings": row.warnings
            })
        
        return {
            "run_id": run_id,
            "status": run.status.value,
            "metrics": run.metrics,
            "preview": preview_data
        }