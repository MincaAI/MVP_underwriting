#!/usr/bin/env python3
"""
File upload routes with SQS-based asynchronous processing.
"""

import hashlib
import uuid
import logging
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, Form, UploadFile, Depends
from sqlalchemy.orm import Session
from .deps import get_session, get_db_session, Case, Run, Component, RunStatus, upload_bytes
import sys
import pathlib

# Add packages to path for local development
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "mq" / "src"))

from app.mq.queue_factory import QueueFactory

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# File validation constants
ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.pdf'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
S3_BUCKET = os.getenv('S3_BUCKET_RAW', 'raw')

def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file meets requirements"""
    if not file.filename:
        return False, "No filename provided"
    
    # Check file extension
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {file_ext} not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check file size (note: this is approximate as we haven't read the content yet)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        return False, f"File size {file.size} bytes exceeds maximum {MAX_FILE_SIZE} bytes"
    
    return True, ""

def compute_file_hash(content: bytes) -> str:
    """Compute SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

def generate_s3_key(case_id: str, attachment_index: int, file_hash: str, filename: str) -> str:
    """Generate S3 key following naming convention: s3://raw/{yyyy}/{mm}/{case_id}/att-{n}-{sha256}.ext"""
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    file_ext = os.path.splitext(filename.lower())[1]
    key = f"raw/{year}/{month}/{case_id}/att-{attachment_index}-{file_hash}{file_ext}"
    return key

@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    profile: str = Form("generic.yaml"),
    case_id: Optional[str] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Upload a file and start asynchronous processing via SQS.
    
    Args:
        file: The file to upload
        profile: Broker profile to use for processing
        case_id: Optional case ID (will be generated if not provided)
    
    Returns:
        Case ID and Run ID for tracking processing status
    """
    logger.info(f"Processing file upload: {file.filename}")
    
    # Validate file
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        logger.error(f"File validation failed: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Generate case_id if not provided
    if not case_id:
        case_id = str(uuid.uuid4())
    
    # Generate run_id for tracking
    run_id = str(uuid.uuid4())
    
    try:
        # Read file content
        content_bytes = await file.read()
        
        # Validate file size after reading
        if len(content_bytes) > MAX_FILE_SIZE:
            logger.error(f"File {file.filename} size {len(content_bytes)} exceeds maximum {MAX_FILE_SIZE}")
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} size {len(content_bytes)} bytes exceeds maximum {MAX_FILE_SIZE} bytes"
            )
        
        # Compute hash
        file_hash = compute_file_hash(content_bytes)
        logger.debug(f"File {file.filename} hash: {file_hash}")
        
        # Generate S3 key
        s3_key = generate_s3_key(case_id, 0, file_hash, file.filename)
        logger.info(f"Uploading to S3 key: {s3_key}")
        
        # Upload to S3
        s3_uri = upload_bytes(
            bucket=S3_BUCKET,
            key=s3_key,
            content=content_bytes,
            content_type=file.content_type or 'application/octet-stream'
        )
        logger.info(f"Successfully uploaded to: {s3_uri}")
        
        # Create case record
        case = Case(
            id=case_id,
            description=f"File upload: {file.filename}",
            status="processing",
            created_at=datetime.utcnow()
        )
        session.add(case)
        
        # Create run record
        run = Run(
            id=run_id,
            case_id=case_id,
            component=Component.EXTRACT,
            status=RunStatus.STARTED,
            profile=profile,
            started_at=datetime.utcnow()
        )
        session.add(run)
        session.commit()
        
        # Send message to SQS
        publisher = QueueFactory.get_publisher()
        message = {
            "msg_id": str(uuid.uuid4()),
            "case_id": case_id,
            "run_id": run_id,
            "component": "EXTRACT",
            "payload": {
                "s3_uri": s3_uri,
                "file_name": file.filename,
                "profile": profile,
                "file_size": len(content_bytes),
                "file_hash": file_hash
            }
        }
        
        await publisher.send_message("mvp-underwriting-extractor", message)
        logger.info(f"Sent EXTRACT message for run {run_id}")
        
        return {
            "case_id": case_id,
            "run_id": run_id,
            "status": "queued",
            "message": "File uploaded successfully and queued for processing",
            "s3_uri": s3_uri
        }
        
    except Exception as e:
        logger.error(f"Error processing file upload: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    profile: str = Form("generic.yaml"),
    case_id: Optional[str] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Upload multiple files and start asynchronous processing via SQS.
    
    Args:
        files: List of files to upload
        profile: Broker profile to use for processing
        case_id: Optional case ID (will be generated if not provided)
    
    Returns:
        Case ID and list of Run IDs for tracking processing status
    """
    logger.info(f"Processing {len(files)} file uploads")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Generate case_id if not provided
    if not case_id:
        case_id = str(uuid.uuid4())
    
    results = []
    publisher = QueueFactory.get_publisher()
    
    try:
        # Create case record
        case = Case(
            id=case_id,
            description=f"Multiple file upload: {len(files)} files",
            status="processing",
            created_at=datetime.utcnow()
        )
        session.add(case)
        
        # Process each file
        for i, file in enumerate(files):
            # Validate file
            is_valid, error_msg = validate_file(file)
            if not is_valid:
                logger.error(f"File {i+1} validation failed: {error_msg}")
                raise HTTPException(status_code=400, detail=f"File {i+1} ({file.filename}): {error_msg}")
            
            # Generate run_id for tracking
            run_id = str(uuid.uuid4())
            
            # Read file content
            content_bytes = await file.read()
            
            # Validate file size after reading
            if len(content_bytes) > MAX_FILE_SIZE:
                logger.error(f"File {file.filename} size {len(content_bytes)} exceeds maximum {MAX_FILE_SIZE}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"File {file.filename} size {len(content_bytes)} bytes exceeds maximum {MAX_FILE_SIZE} bytes"
                )
            
            # Compute hash
            file_hash = compute_file_hash(content_bytes)
            
            # Generate S3 key
            s3_key = generate_s3_key(case_id, i, file_hash, file.filename)
            
            # Upload to S3
            s3_uri = upload_bytes(
                bucket=S3_BUCKET,
                key=s3_key,
                content=content_bytes,
                content_type=file.content_type or 'application/octet-stream'
            )
            
            # Create run record
            run = Run(
                id=run_id,
                case_id=case_id,
                component=Component.EXTRACT,
                status=RunStatus.STARTED,
                profile=profile,
                started_at=datetime.utcnow()
            )
            session.add(run)
            
            # Send message to SQS
            message = {
                "msg_id": str(uuid.uuid4()),
                "case_id": case_id,
                "run_id": run_id,
                "component": "EXTRACT",
                "payload": {
                    "s3_uri": s3_uri,
                    "file_name": file.filename,
                    "profile": profile,
                    "file_size": len(content_bytes),
                    "file_hash": file_hash
                }
            }
            
            await publisher.send_message("mvp-underwriting-extractor", message)
            
            results.append({
                "file_name": file.filename,
                "run_id": run_id,
                "s3_uri": s3_uri,
                "status": "queued"
            })
        
        session.commit()
        
        return {
            "case_id": case_id,
            "status": "queued",
            "message": f"Successfully uploaded {len(files)} files and queued for processing",
            "files": results
        }
        
    except Exception as e:
        logger.error(f"Error processing multiple file uploads: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
