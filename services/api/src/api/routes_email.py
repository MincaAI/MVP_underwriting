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

@router.get("/emails")
async def list_emails(
    limit: int = 50,
    offset: int = 0,
    status_filter: str = None
):
    """List all email messages with case information for smart intake dashboard"""
    db = get_session()
    try:
        # Base query with joins
        query = db.query(EmailMessage).outerjoin(Case, EmailMessage.id == Case.email_message_id)
        
        # Apply status filter if provided
        if status_filter and status_filter != "all":
            if status_filter == "processed":
                query = query.filter(Case.id.isnot(None))
            elif status_filter == "unprocessed":
                query = query.filter(Case.id.is_(None))
            elif status_filter in ["NEW", "EXTRACTING", "TRANSFORMING", "CODIFYING", "REVIEW", "READY", "EXPORTED", "ERROR"]:
                query = query.filter(Case.status == status_filter)
        
        # Order by received date (newest first) and apply pagination
        emails = query.order_by(EmailMessage.received_at.desc()).offset(offset).limit(limit).all()
        
        # Get total count for pagination
        total_count = db.query(EmailMessage).count()
        
        # Format response
        email_list = []
        for email in emails:
            # Get associated case
            case = db.query(Case).filter(Case.email_message_id == email.id).first()
            
            # Count attachments
            attachment_count = len(email.attachments)
            
            # Determine processing status and pre-analysis status
            if case:
                processing_status = case.status.value if hasattr(case.status, 'value') else str(case.status)
                cot_number = case.id  # Using case ID as COT for now
                
                # Use the new pre_analysis_status field
                pre_analysis_status = case.pre_analysis_status or "pending"
                pre_analysis = "Completo" if pre_analysis_status == "complete" else "Incompleto"
                
                # Include missing requirements if available
                missing_reqs = case.missing_requirements or {}
                details_parts = []
                if attachment_count > 0:
                    details_parts.append(f"{attachment_count} attachment(s)")
                if missing_reqs and pre_analysis_status in ["incomplete", "requires_info"]:
                    missing_fields = missing_reqs.get("missing_fields", [])
                    if missing_fields:
                        details_parts.append(f"Missing: {', '.join(missing_fields)}")
                details = "; ".join(details_parts) if details_parts else "No attachments"
            else:
                processing_status = "pending"
                cot_number = None
                pre_analysis = "Incompleto"
                pre_analysis_status = "pending"
                details = f"{attachment_count} attachment(s)" if attachment_count > 0 else "No attachments"
            
            email_data = {
                "id": str(email.id),
                "description": f"Email: {email.subject}",
                "contact": email.from_email,
                "date": email.received_at.strftime("%Y-%m-%d %H:%M"),
                "cotNumber": cot_number or "N/A",
                "preAnalysis": pre_analysis,
                "status": processing_status,
                "company": email.from_email.split('@')[1] if '@' in email.from_email else None,
                "details": details,
                "email_id": email.id,
                "case_id": case.id if case else None,
                "attachment_count": attachment_count,
                "received_at": email.received_at.isoformat(),
                "subject": email.subject,
                "from_email": email.from_email,
                # New pre-analysis fields
                "pre_analysis_status": pre_analysis_status,
                "pre_analysis_completed_at": case.pre_analysis_completed_at.isoformat() if case and case.pre_analysis_completed_at else None,
                "missing_requirements": case.missing_requirements if case else None,
                "pre_analysis_notes": case.pre_analysis_notes if case else None
            }
            email_list.append(email_data)
        
        return {
            "emails": email_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    finally:
        db.close()

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

@router.post("/email/{email_id}/process")
async def process_email(email_id: int):
    """Process an email to create a case and start extraction"""
    db = get_session()
    try:
        # Check if email exists
        email = db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email message not found")
        
        # Check if case already exists
        existing_case = db.query(Case).filter(Case.email_message_id == email_id).first()
        if existing_case:
            return {
                "message": "Email already processed",
                "case_id": existing_case.id,
                "status": existing_case.status.value if hasattr(existing_case.status, 'value') else str(existing_case.status)
            }
        
        # Create new case
        case_id = str(uuid.uuid4())
        case = Case(
            id=case_id,
            source='email',
            email_message_id=email_id,
            filename=f"Email: {email.subject}"
        )
        db.add(case)
        
        # Create initial run for EXTRACT component
        run_id = str(uuid.uuid4())
        run = Run(
            id=run_id,
            case_id=case_id,
            component=Component.EXTRACT,
            status=RunStatus.STARTED,
            profile='generic.yaml',
            started_at=datetime.utcnow(),
            metrics={'email_message_id': email_id, 'attachments_count': len(email.attachments)}
        )
        db.add(run)
        
        db.commit()
        
        # Send SQS messages for processing if there are attachments
        if email.attachments:
            publisher = QueueFactory.get_publisher()
            sqs_messages_sent = 0
            
            for i, attachment in enumerate(email.attachments):
                try:
                    message = {
                        "msg_id": str(uuid.uuid4()),
                        "case_id": case_id,
                        "run_id": run_id,
                        "component": "EXTRACT",
                        "payload": {
                            "s3_uri": attachment.s3_uri,
                            "file_name": attachment.original_name,
                            "profile": 'generic.yaml',
                            "file_size": attachment.file_size,
                            "file_hash": attachment.sha256,
                            "attachment_index": i,
                            "email_message_id": email_id
                        }
                    }
                    
                    await publisher.send_message("mvp-underwriting-extractor", message)
                    sqs_messages_sent += 1
                    logger.info(f"Sent EXTRACT message for attachment: {attachment.original_name}")
                    
                except Exception as sqs_error:
                    logger.error(f"Failed to send SQS message for attachment {attachment.original_name}: {sqs_error}")
        
        return {
            "case_id": case_id,
            "run_id": run_id,
            "status": "processing",
            "message": f"Email processing started with {len(email.attachments)} attachments"
        }
        
    except Exception as e:
        logger.error(f"Error processing email {email_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        db.close()

@router.put("/case/{case_id}/pre-analysis")
async def update_pre_analysis_status(
    case_id: str,
    pre_analysis_status: str = Form(...),
    missing_requirements: str = Form(None),
    pre_analysis_notes: str = Form(None)
):
    """Update pre-analysis status for a case"""
    db = get_session()
    try:
        # Check if case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Validate pre_analysis_status
        valid_statuses = ["pending", "in_progress", "complete", "incomplete", "requires_info"]
        if pre_analysis_status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid pre_analysis_status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update pre-analysis fields
        case.pre_analysis_status = pre_analysis_status
        case.pre_analysis_notes = pre_analysis_notes
        
        # Parse missing_requirements if provided
        if missing_requirements:
            try:
                import json
                case.missing_requirements = json.loads(missing_requirements)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for missing_requirements")
        
        # Set completion timestamp if status is complete
        if pre_analysis_status == "complete":
            case.pre_analysis_completed_at = datetime.utcnow()
        elif pre_analysis_status in ["pending", "in_progress", "incomplete", "requires_info"]:
            case.pre_analysis_completed_at = None
        
        case.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "case_id": case_id,
            "pre_analysis_status": case.pre_analysis_status,
            "pre_analysis_completed_at": case.pre_analysis_completed_at.isoformat() if case.pre_analysis_completed_at else None,
            "missing_requirements": case.missing_requirements,
            "pre_analysis_notes": case.pre_analysis_notes,
            "message": "Pre-analysis status updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating pre-analysis status for case {case_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    finally:
        db.close()
