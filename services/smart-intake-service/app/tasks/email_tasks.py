import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime

from app.mq.queue_factory import QueueFactory, QueueNames
from ..auth.graph_client import GraphAPIClient
from ..processors.email_processor import EmailProcessor
from ..processors.attachment_handler import AttachmentHandler
from ..integrations.vehicle_matcher import VehicleMatcherClient
from ..integrations.database_client import DatabaseClient
from ..config.settings import get_settings

logger = structlog.get_logger()


async def process_email_task(message_id: str,
                            change_type: str = "created",
                            subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Main email processing function (replaces Celery task).

    Args:
        message_id: Microsoft Graph message ID
        change_type: Type of change (created, updated)
        subscription_id: Graph subscription ID

    Returns:
        Processing result summary
    """
    start_time = time.time()
    task_id = str(uuid.uuid4())

    try:
        logger.info("Starting email processing task",
                   task_id=task_id,
                   message_id=message_id,
                   change_type=change_type)

        # Run async processing
        result = await _process_email_async(
            message_id=message_id,
            change_type=change_type,
            subscription_id=subscription_id,
            task_id=task_id
        )

        processing_time = time.time() - start_time

        logger.info("Email processing task completed",
                   task_id=task_id,
                   message_id=message_id,
                   processing_time=processing_time,
                   result=result)

        return {
            "success": True,
            "task_id": task_id,
            "message_id": message_id,
            "processing_time": processing_time,
            "result": result
        }

    except Exception as exc:
        processing_time = time.time() - start_time

        logger.error("Email processing task failed",
                    task_id=task_id,
                    message_id=message_id,
                    processing_time=processing_time,
                    error=str(exc))

        return {
            "success": False,
            "task_id": task_id,
            "message_id": message_id,
            "processing_time": processing_time,
            "error": str(exc),
            "max_retries_exceeded": True
        }


async def queue_email_processing(message_id: str,
                                change_type: str = "created",
                                subscription_id: Optional[str] = None) -> str:
    """
    Queue email processing task using MQ.

    Args:
        message_id: Microsoft Graph message ID
        change_type: Type of change (created, updated)
        subscription_id: Graph subscription ID

    Returns:
        Task ID for tracking
    """
    task_id = str(uuid.uuid4())

    # Create message payload
    message_payload = {
        "task_id": task_id,
        "message_id": message_id,
        "change_type": change_type,
        "subscription_id": subscription_id,
        "task_type": "email_processing"
    }

    # Get MQ publisher and send message
    publisher = QueueFactory.get_publisher()
    await publisher.send_message(
        QueueNames.PRE_ANALYSIS,
        message_payload
    )

    logger.info("Email processing queued",
               task_id=task_id,
               message_id=message_id,
               queue=QueueNames.PRE_ANALYSIS)

    return task_id


async def _process_email_async(message_id: str, 
                              change_type: str,
                              subscription_id: Optional[str],
                              task_id: str) -> Dict[str, Any]:
    """
    Async email processing implementation.
    
    Args:
        message_id: Microsoft Graph message ID
        change_type: Type of change
        subscription_id: Graph subscription ID
        task_id: Celery task ID
        
    Returns:
        Processing result
    """
    settings = get_settings()
    
    # Initialize clients
    graph_client = GraphAPIClient()
    email_processor = EmailProcessor()
    attachment_handler = AttachmentHandler()
    vehicle_matcher = VehicleMatcherClient()
    database_client = DatabaseClient()
    
    try:
        # Step 1: Check if message already processed
        existing_message = await database_client.get_message_by_provider_id(message_id)
        if existing_message and existing_message.get("status") == "PROCESSED":
            logger.info("Message already processed, skipping", 
                       message_id=message_id,
                       existing_cot=existing_message.get("cot_number"))
            return {
                "status": "already_processed",
                "cot_number": existing_message.get("cot_number"),
                "message_id": message_id
            }
        
        # Step 2: Fetch email from Microsoft Graph
        logger.info("Fetching email from Graph API", message_id=message_id)
        email_data = await graph_client.get_message(message_id, expand_attachments=True)
        
        # Step 3: Create or update message record
        message_record = await database_client.create_or_update_message(
            provider_id=message_id,
            email_data=email_data,
            status="PROCESSING"
        )
        
        # Step 4: Process email content
        logger.info("Processing email content", message_id=message_id)
        processed_email = await email_processor.process_email(email_data)
        
        # Step 5: Process attachments
        attachments_data = []
        if email_data.get("attachments"):
            logger.info("Processing attachments", 
                       message_id=message_id,
                       attachment_count=len(email_data["attachments"]))
            
            for attachment in email_data["attachments"]:
                try:
                    attachment_data = await attachment_handler.process_attachment(
                        message_id=message_id,
                        attachment_info=attachment,
                        graph_client=graph_client
                    )
                    attachments_data.append(attachment_data)
                except Exception as e:
                    logger.error("Failed to process attachment", 
                               message_id=message_id,
                               attachment_id=attachment.get("id"),
                               error=str(e))
        
        # Step 6: Extract vehicle information
        logger.info("Extracting vehicle information", message_id=message_id)
        vehicle_descriptions = await email_processor.extract_vehicle_descriptions(
            processed_email, attachments_data
        )
        
        if not vehicle_descriptions:
            logger.warning("No vehicle descriptions found", message_id=message_id)
            await database_client.update_message_status(
                message_record["id"], "NEEDS_REVIEW", 
                missing=["vehicle_descriptions"]
            )
            return {
                "status": "no_vehicles_found",
                "message_id": message_id,
                "requires_review": True
            }
        
        # Step 7: Match vehicles to CVEGS codes
        logger.info("Matching vehicles to CVEGS codes", 
                   message_id=message_id,
                   vehicle_count=len(vehicle_descriptions))
        
        vehicle_inputs = [
            {"description": desc, "insurer_id": "default"}
            for desc in vehicle_descriptions
        ]
        
        match_results = await vehicle_matcher.match_batch_vehicles(vehicle_inputs)
        
        # Step 8: Extract case information
        case_data = await email_processor.extract_case_information(
            processed_email, attachments_data
        )
        
        # Step 9: Create case with vehicles
        logger.info("Creating case with vehicles", 
                   message_id=message_id,
                   vehicle_count=len(vehicle_descriptions))
        
        case = await database_client.create_case_with_vehicles(
            message_id=message_record["id"],
            case_data=case_data,
            vehicle_descriptions=vehicle_descriptions,
            match_results=match_results.get("results", [])
        )
        
        # Step 10: Calculate overall confidence
        overall_confidence = _calculate_overall_confidence(match_results.get("results", []))
        
        # Step 11: Update message status
        final_status = "PROCESSED" if overall_confidence >= 0.7 else "NEEDS_REVIEW"
        missing_fields = _identify_missing_fields(case_data, match_results.get("results", []))
        
        await database_client.update_message_status(
            message_record["id"], 
            final_status,
            cot_number=case["cot_number"],
            confidence=overall_confidence,
            missing=missing_fields
        )
        
        logger.info("Email processing completed successfully", 
                   message_id=message_id,
                   cot_number=case["cot_number"],
                   overall_confidence=overall_confidence,
                   final_status=final_status)
        
        return {
            "status": "success",
            "message_id": message_id,
            "cot_number": case["cot_number"],
            "vehicle_count": len(vehicle_descriptions),
            "overall_confidence": overall_confidence,
            "final_status": final_status,
            "requires_review": final_status == "NEEDS_REVIEW",
            "missing_fields": missing_fields
        }
        
    except Exception as e:
        logger.error("Email processing failed", 
                    message_id=message_id,
                    task_id=task_id,
                    error=str(e))
        
        # Update message status to ERROR
        try:
            await database_client.update_message_status(
                message_record["id"] if 'message_record' in locals() else None,
                "ERROR"
            )
        except Exception as db_error:
            logger.error("Failed to update message status to ERROR", 
                        message_id=message_id,
                        error=str(db_error))
        
        raise


def _calculate_overall_confidence(match_results: List[Dict[str, Any]]) -> float:
    """
    Calculate overall confidence score for the case.
    
    Args:
        match_results: List of vehicle matching results
        
    Returns:
        Overall confidence score (0.0 - 1.0)
    """
    if not match_results:
        return 0.0
    
    # Calculate weighted average confidence
    total_confidence = 0.0
    valid_matches = 0
    
    for result in match_results:
        confidence = result.get("confidence_score", 0.0)
        if confidence > 0.0:  # Only count valid matches
            total_confidence += confidence
            valid_matches += 1
    
    if valid_matches == 0:
        return 0.0
    
    average_confidence = total_confidence / valid_matches
    
    # Apply penalty for low match rate
    match_rate = valid_matches / len(match_results)
    if match_rate < 0.8:  # If less than 80% of vehicles matched
        average_confidence *= match_rate
    
    return round(average_confidence, 2)


def _identify_missing_fields(case_data: Dict[str, Any], 
                           match_results: List[Dict[str, Any]]) -> List[str]:
    """
    Identify missing required fields.
    
    Args:
        case_data: Extracted case information
        match_results: Vehicle matching results
        
    Returns:
        List of missing field names
    """
    missing = []
    
    # Check required case fields
    required_case_fields = ["client_name", "broker_email"]
    for field in required_case_fields:
        if not case_data.get(field):
            missing.append(field)
    
    # Check vehicle matching quality
    low_confidence_vehicles = [
        r for r in match_results 
        if r.get("confidence_score", 0.0) < 0.5
    ]
    
    if low_confidence_vehicles:
        missing.append("vehicle_matching_confidence")
    
    # Check for unmatched vehicles
    unmatched_vehicles = [
        r for r in match_results 
        if r.get("cvegs_code") in ["NO_MATCH", "ERROR"]
    ]
    
    if unmatched_vehicles:
        missing.append("vehicle_cvegs_codes")
    
    return missing


async def reprocess_email_task(message_id: str, reason: str = "manual_retry") -> Dict[str, Any]:
    """
    Reprocess an email (for manual retry or corrections).

    Args:
        message_id: Microsoft Graph message ID
        reason: Reason for reprocessing

    Returns:
        Reprocessing result
    """
    task_id = str(uuid.uuid4())

    try:
        logger.info("Starting email reprocessing",
                   task_id=task_id,
                   message_id=message_id,
                   reason=reason)

        # Run the same processing logic
        result = await _process_email_async(
            message_id=message_id,
            change_type="reprocess",
            subscription_id=None,
            task_id=task_id
        )

        logger.info("Email reprocessing completed",
                   task_id=task_id,
                   message_id=message_id,
                   result=result)

        return result

    except Exception as exc:
        logger.error("Email reprocessing failed",
                    task_id=task_id,
                    message_id=message_id,
                    error=str(exc))

        return {
            "success": False,
            "task_id": task_id,
            "message_id": message_id,
            "error": str(exc),
            "reprocessing_failed": True
        }


async def queue_batch_processing(folder_id: str, limit: int = 50) -> str:
    """
    Queue batch processing of emails from a folder.

    Args:
        folder_id: Outlook folder ID
        limit: Maximum number of emails to process

    Returns:
        Batch processing task ID
    """
    task_id = str(uuid.uuid4())

    # Create message payload
    message_payload = {
        "task_id": task_id,
        "folder_id": folder_id,
        "limit": limit,
        "task_type": "batch_processing"
    }

    # Get MQ publisher and send message
    publisher = QueueFactory.get_publisher()
    await publisher.send_message(
        QueueNames.PRE_ANALYSIS,
        message_payload
    )

    logger.info("Batch processing queued",
               task_id=task_id,
               folder_id=folder_id,
               limit=limit,
               queue=QueueNames.PRE_ANALYSIS)

    return task_id


async def _batch_process_folder_async(folder_id: str,
                                     limit: int,
                                     task_id: str) -> Dict[str, Any]:
    """
    Async implementation of batch folder processing.

    Args:
        folder_id: Folder ID to process
        limit: Maximum messages to process
        task_id: Task ID

    Returns:
        Batch processing result
    """
    graph_client = GraphAPIClient()
    database_client = DatabaseClient()

    try:
        # Get messages from folder
        messages = await graph_client.list_messages_in_folder(folder_id, limit)

        logger.info("Retrieved messages for batch processing",
                   folder_id=folder_id,
                   message_count=len(messages))

        processed_count = 0
        skipped_count = 0
        error_count = 0

        for message in messages:
            message_id = message.get("id")
            if not message_id:
                continue

            try:
                # Check if already processed
                existing = await database_client.get_message_by_provider_id(message_id)
                if existing and existing.get("status") == "PROCESSED":
                    skipped_count += 1
                    continue

                # Queue individual processing task
                await queue_email_processing(
                    message_id=message_id,
                    change_type="batch_process"
                )

                processed_count += 1

            except Exception as e:
                logger.error("Failed to queue message for batch processing",
                           message_id=message_id,
                           error=str(e))
                error_count += 1

        return {
            "folder_id": folder_id,
            "total_messages": len(messages),
            "processed": processed_count,
            "skipped": skipped_count,
            "errors": error_count,
            "queued_tasks": processed_count
        }

    except Exception as e:
        logger.error("Batch folder processing failed",
                    folder_id=folder_id,
                    task_id=task_id,
                    error=str(e))
        raise


async def cleanup_old_tasks_task(days_old: int = 7) -> Dict[str, Any]:
    """
    Cleanup old completed tasks and results.

    Args:
        days_old: Remove tasks older than this many days

    Returns:
        Cleanup result
    """
    task_id = str(uuid.uuid4())

    try:
        logger.info("Starting task cleanup",
                   task_id=task_id,
                   days_old=days_old)

        # In production, this would clean up:
        # - Completed task results
        # - Temporary files
        # - Cache entries
        # - Log files

        # For now, return placeholder result
        return {
            "success": True,
            "task_id": task_id,
            "days_old": days_old,
            "cleaned_tasks": 0,  # Would be actual count
            "cleaned_files": 0,  # Would be actual count
            "freed_space_mb": 0  # Would be actual space freed
        }

    except Exception as exc:
        logger.error("Task cleanup failed",
                    task_id=task_id,
                    error=str(exc))
        raise


async def health_check_task() -> Dict[str, Any]:
    """
    Health check function to verify system functionality.

    Returns:
        Health check result
    """
    task_id = str(uuid.uuid4())

    try:
        # Test basic functionality
        test_data = {
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "smart-intake-service"
        }

        logger.info("Health check executed", **test_data)

        return {
            "healthy": True,
            "test_data": test_data
        }

    except Exception as exc:
        logger.error("Health check failed",
                    task_id=task_id,
                    error=str(exc))
        return {
            "healthy": False,
            "error": str(exc),
            "task_id": task_id
        }


# Task monitoring utilities
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a specific task.

    Args:
        task_id: Task ID

    Returns:
        Task status information
    """
    try:
        # In MQ implementation, we don't have direct task status tracking
        # This would need to be implemented with a task status tracking system
        return {
            "task_id": task_id,
            "status": "UNKNOWN",  # Would be implemented with task tracking
            "result": None,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Task status tracking not implemented in MQ version"
        }

    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        return {
            "task_id": task_id,
            "status": "UNKNOWN",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def get_queue_statistics() -> Dict[str, Any]:
    """
    Get statistics about message queues.

    Returns:
        Queue statistics
    """
    try:
        # Get MQ configuration
        config = QueueFactory.get_config()

        # In a full implementation, this would query actual queue statistics
        # For now, return configuration-based information
        return {
            "queue_backend": config.get("backend"),
            "environment": config.get("environment"),
            "available_queues": list(config.get("queue_names", {}).keys()),
            "queue_names": config.get("queue_names", {}),
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Queue statistics would be implemented with actual queue monitoring"
        }

    except Exception as e:
        logger.error("Failed to get queue statistics", error=str(e))
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def start_message_consumer(queue_name: str, handler: callable):
    """
    Start a message consumer for a specific queue.

    Args:
        queue_name: Name of the queue to consume from
        handler: Function to handle messages
    """
    try:
        consumer = QueueFactory.get_consumer(queue_name)
        await consumer.consume(handler)
    except Exception as e:
        logger.error("Failed to start message consumer",
                    queue_name=queue_name,
                    error=str(e))
        raise


def create_message_handler():
    """
    Create a message handler for processing different types of messages.

    Returns:
        Message handler function
    """
    async def message_handler(message: Dict[str, Any]):
        """Handle incoming messages from the queue."""
        try:
            message_type = message.get("task_type")

            if message_type == "email_processing":
                # Handle email processing messages
                await process_email_task(
                    message_id=message["message_id"],
                    change_type=message.get("change_type", "created"),
                    subscription_id=message.get("subscription_id")
                )

            elif message_type == "batch_processing":
                # Handle batch processing messages
                await _batch_process_folder_async(
                    folder_id=message["folder_id"],
                    limit=message.get("limit", 50),
                    task_id=message["task_id"]
                )

            else:
                logger.warning("Unknown message type received",
                             message_type=message_type,
                             message=message)

        except Exception as e:
            logger.error("Error handling message",
                        message=message,
                        error=str(e))
            raise

    return message_handler
