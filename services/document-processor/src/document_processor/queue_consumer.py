#!/usr/bin/env python3
"""
Simplified document processor consumer for preprocessing data for matching.
Handles EXTRACT → TRANSFORM pipeline and saves results to database.
"""

import asyncio
import tempfile
import os
import logging
import sys
import pathlib
from typing import Dict, Any
import pandas as pd

# Add packages to path for local development
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "db" / "src"))
sys.path.insert(0, str(project_root / "packages" / "storage" / "src"))
sys.path.insert(0, str(project_root / "packages" / "schemas" / "src"))
sys.path.insert(0, str(project_root / "packages" / "mq" / "src"))

from app.db.session import engine
from app.db.models import Run, Row, Component, RunStatus
from app.storage.s3 import download_file
from app.mq.queue_factory import QueueFactory

logger = logging.getLogger(__name__)

class DocumentProcessorConsumer:
    """Consumer for preprocessing documents for matching"""
    
    def __init__(self):
        self.temp_dir = "/tmp/document_processor"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def handle_extract_message(self, message: Dict[str, Any]):
        """Handle EXTRACT component messages"""
        try:
            payload = message["payload"]
            s3_uri = payload["s3_uri"]
            run_id = message["run_id"]
            case_id = message["case_id"]
            profile = payload.get("profile", "generic.yaml")
            
            logger.info(f"Processing EXTRACT message for run {run_id}")
            
            # Update run status to STARTED
            await self._update_run_status(run_id, RunStatus.STARTED)
            
            # Download file from S3
            temp_file_path = os.path.join(self.temp_dir, f"{run_id}.xlsx")
            await self._download_file(s3_uri, temp_file_path)
            
            # Extract data
            extracted_data = await self._extract_data(temp_file_path, run_id, case_id)
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
            # Update run status to SUCCESS
            await self._update_run_status(
                run_id, 
                RunStatus.SUCCESS, 
                metrics={"rows_extracted": len(extracted_data)}
            )
            
            # Send to TRANSFORM queue
            transform_message = {
                "msg_id": message["msg_id"],
                "case_id": case_id,
                "run_id": run_id,
                "component": "TRANSFORM",
                "payload": {
                    "extracted_data": extracted_data,
                    "profile": profile
                }
            }
            
            await QueueFactory.get_publisher().send_message("mvp-underwriting-transform", transform_message)
            logger.info(f"Sent TRANSFORM message for run {run_id}")
            
        except Exception as e:
            logger.error(f"Error processing EXTRACT message: {e}")
            await self._update_run_status(run_id, RunStatus.FAILED, error=str(e))
    
    async def handle_transform_message(self, message: Dict[str, Any]):
        """Handle TRANSFORM component messages - Final stage for matching"""
        try:
            payload = message["payload"]
            run_id = message["run_id"]
            case_id = message["case_id"]
            extracted_data = payload["extracted_data"]
            profile = payload["profile"]
            
            logger.info(f"Processing TRANSFORM message for run {run_id} - Final preprocessing stage")
            
            # Transform data for matching
            transformed_data = await self._transform_data_for_matching(extracted_data, profile, run_id, case_id)
            
            # Update final run status - Processing complete, ready for matching
            await self._update_run_status(
                run_id, 
                RunStatus.SUCCESS, 
                metrics={
                    "rows_processed": len(transformed_data),
                    "ready_for_matching": True,
                    "profile_used": profile
                }
            )
            
            logger.info(f"✅ Preprocessing completed for run {run_id} - {len(transformed_data)} vehicles ready for matching")
            
        except Exception as e:
            logger.error(f"Error processing TRANSFORM message: {e}")
            await self._update_run_status(run_id, RunStatus.FAILED, error=str(e))
    
    async def _download_file(self, s3_uri: str, local_path: str):
        """Download file from S3 to local path"""
        logger.info(f"Downloading {s3_uri} to {local_path}")
        # Implementation would use actual S3 download
        # For now, simulate download with a dummy file
        with open(local_path, 'w') as f:
            f.write("dummy content for testing")
        await asyncio.sleep(0.1)
    
    async def _extract_data(self, file_path: str, run_id: str, case_id: str) -> list:
        """Extract data from file for matching"""
        logger.info(f"Extracting data from {file_path}")
        
        # For testing, create sample data
        # In production, this would parse actual Excel/CSV files
        extracted_data = []
        for i in range(3):  # Sample 3 vehicles
            vehicle_data = {
                "row_index": i,
                "vin": f"1HGBH41JXMN10918{i}",
                "brand": ["TOYOTA", "HONDA", "FORD"][i],
                "model": ["COROLLA", "CIVIC", "F-150"][i],
                "model_year": [2020, 2021, 2019][i],
                "description": f"{['TOYOTA', 'HONDA', 'FORD'][i]} {['COROLLA', 'CIVIC', 'F-150'][i]} {[2020, 2021, 2019][i]}",
                "license_plate": f"ABC-12{i}",
                "raw_data": {
                    "vin": f"1HGBH41JXMN10918{i}",
                    "brand": ["TOYOTA", "HONDA", "FORD"][i],
                    "model": ["COROLLA", "CIVIC", "F-150"][i],
                    "year": [2020, 2021, 2019][i]
                }
            }
            extracted_data.append(vehicle_data)
        
        # Store in database
        await self._store_extracted_data(extracted_data, run_id)
        
        return extracted_data
    
    async def _transform_data_for_matching(self, extracted_data: list, profile: str, run_id: str, case_id: str) -> list:
        """Transform extracted data for vehicle matching"""
        logger.info(f"Transforming {len(extracted_data)} rows for matching with profile {profile}")
        
        transformed_data = []
        for row in extracted_data:
            # Apply transformations for matching
            transformed_row = {
                "row_index": row["row_index"],
                "vin": self._normalize_vin(row.get("vin")),
                "brand": self._normalize_brand(row.get("brand")),
                "model": self._normalize_model(row.get("model")),
                "model_year": self._normalize_year(row.get("model_year")),
                "description": self._normalize_description(row.get("description")),
                "license_plate": self._normalize_plate(row.get("license_plate")),
                "matching_key": self._generate_matching_key(row),  # For efficient matching
                "raw_data": row["raw_data"],
                "profile_used": profile,
                "transformed_at": pd.Timestamp.utcnow().isoformat()
            }
            transformed_data.append(transformed_row)
        
        # Store transformed data in database
        await self._store_transformed_data(transformed_data, run_id)
        
        return transformed_data
    
    def _normalize_vin(self, vin: str) -> str:
        """Normalize VIN for matching"""
        if not vin:
            return None
        return str(vin).strip().upper().replace(' ', '')
    
    def _normalize_brand(self, brand: str) -> str:
        """Normalize brand for matching"""
        if not brand:
            return None
        return str(brand).strip().upper()
    
    def _normalize_model(self, model: str) -> str:
        """Normalize model for matching"""
        if not model:
            return None
        return str(model).strip().upper()
    
    def _normalize_year(self, year) -> int:
        """Normalize year for matching"""
        if not year:
            return None
        try:
            year_int = int(year)
            if 1900 <= year_int <= 2030:
                return year_int
        except (ValueError, TypeError):
            pass
        return None
    
    def _normalize_description(self, description: str) -> str:
        """Normalize description for matching"""
        if not description:
            return None
        return str(description).strip().upper()
    
    def _normalize_plate(self, plate: str) -> str:
        """Normalize license plate for matching"""
        if not plate:
            return None
        return str(plate).strip().upper().replace(' ', '')
    
    def _generate_matching_key(self, row: dict) -> str:
        """Generate a key for efficient matching"""
        brand = self._normalize_brand(row.get("brand", "")) or ""
        model = self._normalize_model(row.get("model", "")) or ""
        year = str(self._normalize_year(row.get("model_year"))) or ""
        return f"{brand}_{model}_{year}"
    
    async def _store_extracted_data(self, extracted_data: list, run_id: str):
        """Store extracted data in database"""
        from sqlalchemy.orm import Session
        
        with Session(engine) as session:
            for row_data in extracted_data:
                row = Row(
                    run_id=run_id,
                    row_index=row_data["row_index"],
                    raw_data=row_data["raw_data"],
                    extracted_data=row_data,
                    created_at=pd.Timestamp.utcnow()
                )
                session.add(row)
            session.commit()
        
        logger.info(f"Stored {len(extracted_data)} extracted rows for run {run_id}")
    
    async def _store_transformed_data(self, transformed_data: list, run_id: str):
        """Store transformed data in database"""
        from sqlalchemy.orm import Session
        
        with Session(engine) as session:
            for row_data in transformed_data:
                row = session.query(Row).filter(
                    Row.run_id == run_id,
                    Row.row_index == row_data["row_index"]
                ).first()
                
                if row:
                    row.transformed_data = row_data
                    row.updated_at = pd.Timestamp.utcnow()
                else:
                    # Create new row if not found
                    row = Row(
                        run_id=run_id,
                        row_index=row_data["row_index"],
                        raw_data=row_data["raw_data"],
                        extracted_data=row_data,
                        transformed_data=row_data,
                        created_at=pd.Timestamp.utcnow()
                    )
                    session.add(row)
            
            session.commit()
        
        logger.info(f"Stored {len(transformed_data)} transformed rows for run {run_id}")
    
    async def _update_run_status(self, run_id: str, status: RunStatus, metrics: dict = None, error: str = None):
        """Update run status in database"""
        from sqlalchemy.orm import Session
        
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = status
                run.finished_at = pd.Timestamp.utcnow()
                
                if metrics:
                    run.metrics = run.metrics or {}
                    run.metrics.update(metrics)
                
                if error:
                    run.metrics = run.metrics or {}
                    run.metrics['error'] = error
                
                session.commit()
                logger.info(f"Updated run {run_id} status to {status.value}")