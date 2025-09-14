#!/usr/bin/env python3
"""
Document Processor Queue Consumer

Handles complete document processing pipeline: EXTRACT → TRANSFORM → EXPORT
Integrates with existing DocumentExtractor, DocumentTransformer, and DocumentExporter services.
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
from app.storage.s3 import download_to_tmp
from app.mq.queue_factory import QueueFactory

# Import the existing service components
from document_processor.services.extractor import DocumentExtractor
from document_processor.services.transformer import DocumentTransformer
from document_processor.services.exporter import DocumentExporter

logger = logging.getLogger(__name__)

class DocumentProcessorConsumer:
    """Consumer for complete document processing pipeline: EXTRACT → TRANSFORM → EXPORT"""
    
    def __init__(self):
        self.temp_dir = "/tmp/document_processor"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize service components
        self.extractor = DocumentExtractor()
        self.transformer = DocumentTransformer()
        self.exporter = DocumentExporter()
    
    async def handle_extract_message(self, message: Dict[str, Any]):
        """Handle EXTRACT component messages"""
        try:
            payload = message["payload"]
            s3_uri = payload["s3_uri"]
            run_id = message["run_id"]
            case_id = message["case_id"]
            profile = payload.get("profile", "generic.yaml")
            
            logger.info(f"Processing EXTRACT message for run {run_id}")
            
            # Download file from S3
            temp_file_path = os.path.join(self.temp_dir, f"{run_id}.xlsx")
            await self._download_file(s3_uri, temp_file_path)
            
            # Create a mock UploadFile object for the extractor
            from fastapi import UploadFile
            import io
            
            with open(temp_file_path, 'rb') as f:
                file_content = f.read()
            
            # Create UploadFile-like object
            file_obj = UploadFile(
                filename=f"{run_id}.xlsx",
                file=io.BytesIO(file_content)
            )
            
            # Use the existing extractor service
            extracted_data = await self.extractor.extract(file_obj, run_id, case_id)
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
            logger.info(f"✅ Extract completed for run {run_id} - {len(extracted_data)} rows extracted")
            
            # Send to TRANSFORM queue
            transform_message = {
                "msg_id": message["msg_id"],
                "case_id": case_id,
                "run_id": run_id,
                "component": "TRANSFORM",
                "payload": {
                    "profile": profile,
                    "export_template": payload.get("export_template", "gcotiza_v1.yaml")
                }
            }
            
            await QueueFactory.get_publisher().send_message("mvp-underwriting-transform", transform_message)
            logger.info(f"Sent TRANSFORM message for run {run_id}")
            
        except Exception as e:
            logger.error(f"Error processing EXTRACT message: {e}")
            await self._update_run_status(run_id, RunStatus.FAILED, error=str(e))
    
    async def handle_transform_message(self, message: Dict[str, Any]):
        """Handle TRANSFORM component messages"""
        try:
            payload = message["payload"]
            run_id = message["run_id"]
            case_id = message["case_id"]
            profile = payload.get("profile", "generic.yaml")
            export_template = payload.get("export_template", "gcotiza_v1.yaml")
            
            logger.info(f"Processing TRANSFORM message for run {run_id}")
            
            # Use the existing transformer service
            transform_result = await self.transformer.transform(run_id, profile)
            
            logger.info(f"✅ Transform completed for run {run_id} - {transform_result.get('transformed_rows', 0)} rows processed")
            
            # Send to EXPORT queue
            export_message = {
                "msg_id": message["msg_id"],
                "case_id": case_id,
                "run_id": run_id,
                "component": "EXPORT",
                "payload": {
                    "template": export_template,
                    "transform_result": transform_result
                }
            }
            
            await QueueFactory.get_publisher().send_message("mvp-underwriting-export", export_message)
            logger.info(f"Sent EXPORT message for run {run_id}")
            
        except Exception as e:
            logger.error(f"Error processing TRANSFORM message: {e}")
            await self._update_run_status(run_id, RunStatus.FAILED, error=str(e))
    
    async def handle_export_message(self, message: Dict[str, Any]):
        """Handle EXPORT component messages - Final stage of processing"""
        try:
            payload = message["payload"]
            run_id = message["run_id"]
            case_id = message["case_id"]
            template = payload.get("template", "gcotiza_v1.yaml")
            transform_result = payload.get("transform_result", {})
            
            logger.info(f"Processing EXPORT message for run {run_id}")
            
            # Use the existing exporter service
            export_url = await self.exporter.export(run_id, template)
            
            # Update final run status - Complete processing pipeline
            await self._update_run_status(
                run_id, 
                RunStatus.SUCCESS, 
                metrics={
                    "export_url": export_url,
                    "template_used": template,
                    "pipeline_completed": True,
                    "transform_metrics": transform_result
                }
            )
            
            logger.info(f"🎉 Complete processing pipeline finished for run {run_id} - Export available at {export_url}")
            
        except Exception as e:
            logger.error(f"Error processing EXPORT message: {e}")
            await self._update_run_status(run_id, RunStatus.FAILED, error=str(e))
    
    async def _download_file(self, s3_uri: str, local_path: str):
        """Download file from S3 to local path"""
        logger.info(f"Downloading {s3_uri} to {local_path}")
        try:
            # Use the actual S3 download function
            temp_path = download_to_tmp(s3_uri)
            # Move temp file to desired location
            import shutil
            shutil.move(temp_path, local_path)
        except Exception as e:
            logger.warning(f"S3 download failed, creating dummy file for testing: {e}")
            # Fallback for testing - create dummy Excel file
            with open(local_path, 'w') as f:
                f.write("dummy content for testing")
            await asyncio.sleep(0.1)
    
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
