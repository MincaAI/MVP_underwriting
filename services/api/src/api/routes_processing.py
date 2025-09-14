"""
Processing status and data retrieval endpoints for the simplified preprocessing pipeline.
"""

import logging
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .deps import get_session, get_db_session, Run, Component, RunStatus, Row

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/processing", tags=["processing"])

@router.get("/status/{run_id}")
async def get_processing_status(run_id: str, db: Session = Depends(get_db_session)):
    """Get processing status for a run"""
    try:
        # Get the main run
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get all related runs (extract, transform)
        all_runs = db.query(Run).filter(Run.case_id == run.case_id).all()
        
        # Calculate overall progress
        total_steps = 2  # EXTRACT + TRANSFORM
        completed_steps = 0
        
        extract_run = None
        transform_run = None
        
        for r in all_runs:
            if r.component == Component.EXTRACT:
                extract_run = r
                if r.status == RunStatus.SUCCESS:
                    completed_steps += 1
            elif r.component == Component.TRANSFORM:
                transform_run = r
                if r.status == RunStatus.SUCCESS:
                    completed_steps += 1
        
        progress_percentage = (completed_steps / total_steps) * 100
        
        # Determine overall status
        if any(r.status == RunStatus.FAILED for r in all_runs):
            overall_status = "failed"
        elif completed_steps == total_steps:
            overall_status = "completed"
        elif completed_steps > 0:
            overall_status = "processing"
        else:
            overall_status = "pending"
        
        return {
            "run_id": run_id,
            "case_id": run.case_id,
            "overall_status": overall_status,
            "progress_percentage": progress_percentage,
            "steps": {
                "extract": {
                    "status": extract_run.status.value if extract_run else "pending",
                    "started_at": extract_run.started_at.isoformat() if extract_run and extract_run.started_at else None,
                    "finished_at": extract_run.finished_at.isoformat() if extract_run and extract_run.finished_at else None,
                    "metrics": extract_run.metrics or {}
                },
                "transform": {
                    "status": transform_run.status.value if transform_run else "pending",
                    "started_at": transform_run.started_at.isoformat() if transform_run and transform_run.started_at else None,
                    "finished_at": transform_run.finished_at.isoformat() if transform_run and transform_run.finished_at else None,
                    "metrics": transform_run.metrics or {}
                }
            },
            "ready_for_matching": transform_run and transform_run.status == RunStatus.SUCCESS and transform_run.metrics.get("ready_for_matching", False)
        }
        
    except Exception as e:
        logger.error(f"Error getting processing status for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{run_id}")
async def get_preprocessed_data(
    run_id: str, 
    db: Session = Depends(get_db_session),
    limit: Optional[int] = 100,
    offset: Optional[int] = 0
):
    """Get preprocessed data for a run (ready for matching)"""
    try:
        # Check if run exists and is completed
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get transformed data
        rows = db.query(Row).filter(
            Row.run_id == run_id,
            Row.transformed_data.isnot(None)
        ).offset(offset).limit(limit).all()
        
        if not rows:
            return {
                "run_id": run_id,
                "total_rows": 0,
                "data": [],
                "message": "No preprocessed data found. Run may still be processing."
            }
        
        # Format data for matching
        preprocessed_data = []
        for row in rows:
            if row.transformed_data:
                vehicle_data = {
                    "row_index": row.row_index,
                    "vin": row.transformed_data.get("vin"),
                    "brand": row.transformed_data.get("brand"),
                    "model": row.transformed_data.get("model"),
                    "model_year": row.transformed_data.get("model_year"),
                    "description": row.transformed_data.get("description"),
                    "license_plate": row.transformed_data.get("license_plate"),
                    "matching_key": row.transformed_data.get("matching_key"),
                    "profile_used": row.transformed_data.get("profile_used"),
                    "transformed_at": row.transformed_data.get("transformed_at")
                }
                preprocessed_data.append(vehicle_data)
        
        # Get total count
        total_count = db.query(Row).filter(
            Row.run_id == run_id,
            Row.transformed_data.isnot(None)
        ).count()
        
        return {
            "run_id": run_id,
            "total_rows": total_count,
            "returned_rows": len(preprocessed_data),
            "offset": offset,
            "limit": limit,
            "data": preprocessed_data,
            "ready_for_matching": True
        }
        
    except Exception as e:
        logger.error(f"Error getting preprocessed data for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{case_id}")
async def get_case_runs(case_id: str, db: Session = Depends(get_db_session)):
    """Get all runs for a case"""
    try:
        runs = db.query(Run).filter(Run.case_id == case_id).order_by(Run.created_at.desc()).all()
        
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found for case")
        
        formatted_runs = []
        for run in runs:
            formatted_runs.append({
                "run_id": run.id,
                "component": run.component.value,
                "status": run.status.value,
                "file_name": run.file_name,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "metrics": run.metrics or {},
                "created_at": run.created_at.isoformat()
            })
        
        return {
            "case_id": case_id,
            "total_runs": len(formatted_runs),
            "runs": formatted_runs
        }
        
    except Exception as e:
        logger.error(f"Error getting runs for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-matching/{run_id}")
async def trigger_vehicle_matching(run_id: str, db: Session = Depends(get_db_session)):
    """Trigger vehicle matching for preprocessed data"""
    try:
        # Check if run exists and is ready for matching
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Check if data is ready for matching
        transform_runs = db.query(Run).filter(
            Run.case_id == run.case_id,
            Run.component == Component.TRANSFORM
        ).all()
        
        ready_for_matching = any(
            r.status == RunStatus.SUCCESS and r.metrics.get("ready_for_matching", False) 
            for r in transform_runs
        )
        
        if not ready_for_matching:
            raise HTTPException(
                status_code=400, 
                detail="Data not ready for matching. Preprocessing may still be in progress."
            )
        
        # Send message to vehicle codifier queue for matching
        from app.mq.queue_factory import QueueFactory
        import uuid
        
        message = {
            "msg_id": str(uuid.uuid4()),
            "case_id": run.case_id,
            "run_id": run_id,
            "component": "CODIFY",
            "payload": {
                "run_id": run_id,
                "case_id": run.case_id,
                "triggered_by": "api",
                "triggered_at": pd.Timestamp.utcnow().isoformat()
            }
        }
        
        publisher = QueueFactory.get_publisher()
        await publisher.send_message("mvp-underwriting-matching", message)
        
        return {
            "run_id": run_id,
            "case_id": run.case_id,
            "status": "matching_triggered",
            "message": "Vehicle matching has been triggered for preprocessed data",
            "message_id": message["msg_id"],
            "next_step": "Check vehicle codifier service for matching results"
        }
        
    except Exception as e:
        logger.error(f"Error triggering matching for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
