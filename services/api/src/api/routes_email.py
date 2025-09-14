import hashlib
import uuid
import logging
import traceback
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, File, Form, UploadFile, Depends
from sqlalchemy.orm import Session
from .deps import get_session, get_db_session, Case, EmailMessage, EmailAttachment, Run, Component, RunStatus, upload_bytes
import os
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

@router.post("/process-manual-email")
async def process_manual_email(
    from_email: str = Form(...),
    subject: str = Form(...),
    received_date: str = Form(...),
    content: str = Form(""),
    attachments: List[UploadFile] = File(...)
):
    """Process manually uploaded email with attachments"""
    
    logger.info(f"Processing manual email from: {from_email}, subject: {subject}, attachments: {len(attachments)}")
    
    if not attachments:
        logger.error("No attachments provided")
        raise HTTPException(status_code=400, detail="At least one attachment is required")
    
    # Validate all files first
    for i, file in enumerate(attachments):
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            logger.error(f"File validation failed for file {i+1} ({file.filename}): {error_msg}")
            raise HTTPException(status_code=400, detail=f"File {i+1} ({file.filename}): {error_msg}")
    
    case_id = str(uuid.uuid4())
    logger.info(f"Generated case_id: {case_id}")
    
    try:
        # Generate unique identifiers
        email_content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Parse received_date
        try:
            received_datetime = datetime.fromisoformat(received_date.replace('Z', '+00:00'))
        except ValueError as date_error:
            logger.warning(f"ISO format parsing failed: {date_error}, trying date-only format")
            try:
                received_datetime = datetime.strptime(received_date, '%Y-%m-%d')
            except ValueError as date_error2:
                logger.error(f"Date parsing failed: {date_error2}")
                raise HTTPException(status_code=400, detail=f"Invalid date format: {received_date}")
        
        # Process attachments and upload to S3
        attachment_data = []
        for i, file in enumerate(attachments):
            try:
                logger.info(f"Processing attachment {i+1}: {file.filename}")
                
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
                s3_key = generate_s3_key(case_id, i, file_hash, file.filename)
                logger.info(f"Uploading to S3 key: {s3_key}")
                
                # Upload to S3
                s3_uri = upload_bytes(
                    bucket=S3_BUCKET,
                    key=s3_key,
                    content=content_bytes,
                    content_type=file.content_type or 'application/octet-stream'
                )
                logger.info(f"Successfully uploaded to: {s3_uri}")
                
                attachment_data.append({
                    'original_name': file.filename,
                    'mime_type': file.content_type or 'application/octet-stream',
                    'file_size': len(content_bytes),
                    'sha256': file_hash,
                    's3_uri': s3_uri
                })
            except Exception as attachment_error:
                logger.error(f"Failed to process attachment {file.filename}: {attachment_error}")
                raise HTTPException(status_code=500, detail=f"Failed to process attachment {file.filename}: {str(attachment_error)}")
        
        # Create database records
        logger.info("Creating database records")
        db = get_session()
        try:
            # Create email message
            email_message = EmailMessage(
                from_email=from_email,
                subject=subject,
                content=content,
                received_at=received_datetime,
                content_hash=email_content_hash
            )
            db.add(email_message)
            db.flush()  # Get the ID
            logger.info(f"Created email_message with ID: {email_message.id}")
            
            # Create email attachments
            for attachment_info in attachment_data:
                email_attachment = EmailAttachment(
                    email_message_id=email_message.id,
                    **attachment_info
                )
                db.add(email_attachment)
            logger.info(f"Created {len(attachment_data)} email attachments")
            
            # Create case
            case = Case(
                id=case_id,
                source='email',
                email_message_id=email_message.id,
                filename=f"{len(attachments)} attachments"
            )
            db.add(case)
            logger.info(f"Created case: {case_id}")
            
            # Create initial run for EXTRACT component
            run_id = str(uuid.uuid4())
            run = Run(
                id=run_id,
                case_id=case_id,
                component=Component.EXTRACT,
                status=RunStatus.STARTED,
                profile='generic.yaml',  # Default profile
                started_at=datetime.utcnow(),
                metrics={'attachments_count': len(attachments)}
            )
            db.add(run)
            logger.info(f"Created run: {run_id}")
            
            db.commit()
            logger.info("Successfully committed database transaction")
            
            # Send SQS messages for each attachment
            publisher = QueueFactory.get_publisher()
            sqs_messages_sent = 0
            
            for i, attachment_info in enumerate(attachment_data):
                try:
                    message = {
                        "msg_id": str(uuid.uuid4()),
                        "case_id": case_id,
                        "run_id": run_id,
                        "component": "EXTRACT",
                        "payload": {
                            "s3_uri": attachment_info['s3_uri'],
                            "file_name": attachment_info['original_name'],
                            "profile": 'generic.yaml',
                            "file_size": attachment_info['file_size'],
                            "file_hash": attachment_info['sha256'],
                            "attachment_index": i,
                            "email_message_id": email_message.id
                        }
                    }
                    
                    await publisher.send_message("mvp-underwriting-extractor", message)
                    sqs_messages_sent += 1
                    logger.info(f"Sent EXTRACT message for attachment {i+1}: {attachment_info['original_name']}")
                    
                except Exception as sqs_error:
                    logger.error(f"Failed to send SQS message for attachment {i+1}: {sqs_error}")
            
            return {
                "case_id": case_id,
                "email_message_id": email_message.id,
                "run_id": run_id,
                "status": "queued",
                "attachments_processed": len(attachments),
                "sqs_messages_sent": sqs_messages_sent,
                "message": f"Successfully processed email with {len(attachments)} attachments and queued {sqs_messages_sent} for processing"
            }
            
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            logger.error(f"Database error traceback: {traceback.format_exc()}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        finally:
            db.close()
        
    except HTTPException:
        # Re-raise HTTP exceptions (they have appropriate status codes already)
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing manual email: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/email/{email_id}")
async def get_email_details(email_id: int):
    """Get email message details with attachments"""
    db = get_session()
    try:
        email = db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email message not found")
        
        return {
            "id": email.id,
            "from_email": email.from_email,
            "subject": email.subject,
            "content": email.content,
            "received_at": email.received_at.isoformat(),
            "content_hash": email.content_hash,
            "created_at": email.created_at.isoformat(),
            "attachments": [
                {
                    "id": att.id,
                    "original_name": att.original_name,
                    "mime_type": att.mime_type,
                    "file_size": att.file_size,
                    "sha256": att.sha256,
                    "s3_uri": att.s3_uri,
                    "created_at": att.created_at.isoformat()
                }
                for att in email.attachments
            ]
        }
    finally:
        db.close()