from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
import httpx
import os

from app.db.session import engine
from app.db.models import Run, Component, RunStatus
import uuid

router = APIRouter(prefix="/codify")

@router.post("/batch")
async def codify_batch(run_id: str | None = None, case_id: str | None = None):
    """
    Run codification batch processing.
    
    Args:
        run_id: Optional existing run ID to process
        case_id: Optional case ID for new runs
        
    Returns:
        Run results with metrics
    """
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
        
        # Call vehicle-codifier service to process the run
        vehicle_codifier_url = os.getenv("VEHICLE_CODIFIER_URL", "http://vehicle-codifier:8002")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{vehicle_codifier_url}/codify/batch",
                    params={"run_id": run_id}
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail=f"Vehicle codifier service error: {e}")
        
        # Get updated run with metrics
        run = s.get(Run, run_id)
        return {"run_id": run_id, "metrics": run.metrics}