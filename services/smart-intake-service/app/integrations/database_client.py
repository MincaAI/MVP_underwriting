from typing import List, Dict, Any, Optional
import httpx
import structlog
from datetime import datetime
import asyncio

from ..config.settings import get_settings

logger = structlog.get_logger()


class DatabaseClient:
    """Client for integrating with the Database Service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.database_service_url
        self.timeout = httpx.Timeout(30.0)
    
    async def create_or_update_message(self, 
                                     provider_id: str,
                                     email_data: Dict[str, Any],
                                     status: str = "NEW") -> Dict[str, Any]:
        """
        Create or update message record in database.
        
        Args:
            provider_id: Microsoft Graph message ID
            email_data: Email data from Graph API
            status: Processing status
            
        Returns:
            Created or updated message record
        """
        try:
            # Extract metadata from email data
            sender = email_data.get("sender", {}).get("emailAddress", {})
            
            message_data = {
                "provider_id": provider_id,
                "subject": email_data.get("subject"),
                "from_name": sender.get("name"),
                "from_email": sender.get("address"),
                "received_at": email_data.get("receivedDateTime"),
                "folder": email_data.get("parentFolderId"),
                "status": status
            }
            
            # For now, we'll use direct database access since we don't have REST API yet
            # In future, this would be an HTTP call to database service
            from ...database_service.app.models.message import Message, MessageStatus
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                # Check if message already exists
                from sqlalchemy import select
                result = await db.execute(
                    select(Message).where(Message.provider_id == provider_id)
                )
                existing_message = result.scalar_one_or_none()
                
                if existing_message:
                    # Update existing message
                    for key, value in message_data.items():
                        if key != "provider_id" and value is not None:
                            setattr(existing_message, key, value)
                    
                    await db.commit()
                    await db.refresh(existing_message)
                    
                    logger.info("Message updated", 
                               provider_id=provider_id,
                               status=status)
                    
                    return existing_message.to_dict()
                else:
                    # Create new message
                    message = Message(**message_data)
                    db.add(message)
                    await db.commit()
                    await db.refresh(message)
                    
                    logger.info("Message created", 
                               provider_id=provider_id,
                               message_id=str(message.id))
                    
                    return message.to_dict()
                    
        except Exception as e:
            logger.error("Failed to create/update message", 
                        provider_id=provider_id,
                        error=str(e))
            raise
    
    async def get_message_by_provider_id(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Get message by Microsoft Graph provider ID.
        
        Args:
            provider_id: Microsoft Graph message ID
            
        Returns:
            Message record or None if not found
        """
        try:
            from ...database_service.app.models.message import Message
            from ...database_service.app.config.database import AsyncSessionLocal
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Message).where(Message.provider_id == provider_id)
                )
                message = result.scalar_one_or_none()
                
                if message:
                    return message.to_dict()
                return None
                
        except Exception as e:
            logger.error("Failed to get message by provider ID", 
                        provider_id=provider_id,
                        error=str(e))
            raise
    
    async def update_message_status(self, 
                                  message_id: str,
                                  status: str,
                                  cot_number: Optional[str] = None,
                                  confidence: Optional[float] = None,
                                  missing: Optional[List[str]] = None) -> bool:
        """
        Update message processing status.
        
        Args:
            message_id: Message ID (UUID)
            status: New status
            cot_number: COT number if case was created
            confidence: Overall confidence score
            missing: List of missing fields
            
        Returns:
            True if update was successful
        """
        try:
            from ...database_service.app.models.message import Message, MessageStatus
            from ...database_service.app.config.database import AsyncSessionLocal
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Message).where(Message.id == message_id)
                )
                message = result.scalar_one_or_none()
                
                if not message:
                    logger.warning("Message not found for status update", message_id=message_id)
                    return False
                
                # Update fields
                message.status = MessageStatus(status)
                if cot_number:
                    message.cot_number = cot_number
                if confidence is not None:
                    message.confidence = confidence
                if missing is not None:
                    message.missing = missing
                
                await db.commit()
                
                logger.info("Message status updated", 
                           message_id=message_id,
                           status=status,
                           cot_number=cot_number)
                
                return True
                
        except Exception as e:
            logger.error("Failed to update message status", 
                        message_id=message_id,
                        status=status,
                        error=str(e))
            raise
    
    async def create_case_with_vehicles(self, 
                                      message_id: str,
                                      case_data: Dict[str, Any],
                                      vehicle_descriptions: List[str],
                                      match_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create case with associated vehicles and CVEGS results.
        
        Args:
            message_id: Message ID (UUID)
            case_data: Case information
            vehicle_descriptions: List of vehicle descriptions
            match_results: CVEGS matching results
            
        Returns:
            Created case record
        """
        try:
            from ...database_service.app.repositories.case_repository import CaseRepository
            from ...database_service.app.repositories.vehicle_repository import VehicleRepository
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                case_repo = CaseRepository(db)
                vehicle_repo = VehicleRepository(db)
                
                # Prepare case data
                case_create_data = {
                    "message_id": message_id,
                    "client_name": case_data.get("client_name"),
                    "client_rfc": case_data.get("client_rfc"),
                    "broker_name": case_data.get("broker_name"),
                    "broker_email": case_data.get("broker_email"),
                    "loss_history": case_data.get("loss_history"),
                    "policy_type": case_data.get("policy_type"),
                    "notes": case_data.get("notes"),
                    "vehicle_count": len(vehicle_descriptions)
                }
                
                # Create case with auto-generated COT
                case = await case_repo.create_case_with_cot(**case_create_data)
                
                # Create vehicles with CVEGS results
                vehicles_data = []
                for i, (description, result) in enumerate(zip(vehicle_descriptions, match_results)):
                    vehicle_data = {
                        "original_description": description,
                        "brand": result.get("matched_brand"),
                        "model": result.get("matched_model"),
                        "year": result.get("matched_year"),
                        "description": result.get("matched_description"),
                        "cvegs_result": result
                    }
                    vehicles_data.append(vehicle_data)
                
                vehicles = await vehicle_repo.bulk_create_vehicles_with_cvegs(
                    str(case.id), vehicles_data
                )
                
                logger.info("Case created with vehicles", 
                           case_id=str(case.id),
                           cot_number=case.cot_number,
                           vehicle_count=len(vehicles))
                
                return case.to_dict()
                
        except Exception as e:
            logger.error("Failed to create case with vehicles", 
                        message_id=message_id,
                        vehicle_count=len(vehicle_descriptions),
                        error=str(e))
            raise
    
    async def create_attachment_record(self, 
                                     message_id: str,
                                     attachment_info: Dict[str, Any],
                                     storage_path: str,
                                     processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create attachment record in database.
        
        Args:
            message_id: Message ID (UUID)
            attachment_info: Attachment metadata from Graph
            storage_path: Path where file is stored
            processing_result: Results from document processing
            
        Returns:
            Created attachment record
        """
        try:
            from ...database_service.app.models.attachment import Attachment
            from ...database_service.app.config.database import AsyncSessionLocal
            import hashlib
            
            async with AsyncSessionLocal() as db:
                # Calculate file hash if content is available
                file_hash = None
                if processing_result.get("file_content"):
                    file_hash = hashlib.sha256(processing_result["file_content"]).hexdigest()
                
                attachment_data = {
                    "message_id": message_id,
                    "name": attachment_info.get("name"),
                    "mime_type": attachment_info.get("contentType"),
                    "size_bytes": attachment_info.get("size"),
                    "storage_path": storage_path,
                    "sha256": file_hash,
                    "is_processed": processing_result.get("status", "processed"),
                    "processing_notes": processing_result.get("notes"),
                    "content_type": processing_result.get("content_type"),
                    "page_count": processing_result.get("page_count"),
                    "sheet_count": processing_result.get("sheet_count"),
                    "extracted_text": processing_result.get("extracted_text"),
                    "extracted_tables": processing_result.get("extracted_tables"),
                    "vehicle_data_found": processing_result.get("vehicle_data_found", "unknown")
                }
                
                attachment = Attachment(**attachment_data)
                db.add(attachment)
                await db.commit()
                await db.refresh(attachment)
                
                logger.info("Attachment record created", 
                           attachment_id=str(attachment.id),
                           filename=attachment.name,
                           vehicle_data_found=attachment.vehicle_data_found)
                
                return attachment.to_dict()
                
        except Exception as e:
            logger.error("Failed to create attachment record", 
                        message_id=message_id,
                        filename=attachment_info.get("name"),
                        error=str(e))
            raise
    
    async def get_case_by_cot(self, cot_number: str) -> Optional[Dict[str, Any]]:
        """
        Get case by COT number.
        
        Args:
            cot_number: COT number
            
        Returns:
            Case record or None if not found
        """
        try:
            from ...database_service.app.repositories.case_repository import CaseRepository
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                case_repo = CaseRepository(db)
                case = await case_repo.get_by_cot_number(cot_number)
                
                if case:
                    return case.to_dict()
                return None
                
        except Exception as e:
            logger.error("Failed to get case by COT", 
                        cot_number=cot_number,
                        error=str(e))
            raise
    
    async def get_cases_needing_review(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get cases that need manual review.
        
        Args:
            limit: Maximum number of cases to return
            
        Returns:
            List of cases needing review
        """
        try:
            from ...database_service.app.repositories.case_repository import CaseRepository
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                case_repo = CaseRepository(db)
                cases = await case_repo.get_cases_needing_review()
                
                # Limit results
                limited_cases = cases[:limit] if cases else []
                
                return [case.to_dict() for case in limited_cases]
                
        except Exception as e:
            logger.error("Failed to get cases needing review", error=str(e))
            raise
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics from database.
        
        Returns:
            Processing statistics
        """
        try:
            from ...database_service.app.repositories.case_repository import CaseRepository
            from ...database_service.app.repositories.vehicle_repository import VehicleRepository
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                case_repo = CaseRepository(db)
                vehicle_repo = VehicleRepository(db)
                
                # Get statistics
                case_stats = await case_repo.get_case_statistics()
                vehicle_stats = await vehicle_repo.get_vehicle_statistics()
                
                combined_stats = {
                    "cases": case_stats,
                    "vehicles": vehicle_stats,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                return combined_stats
                
        except Exception as e:
            logger.error("Failed to get processing statistics", error=str(e))
            raise
    
    async def search_cases(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search cases by text query.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching cases
        """
        try:
            from ...database_service.app.repositories.case_repository import CaseRepository
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                case_repo = CaseRepository(db)
                cases = await case_repo.search_cases(query, limit)
                
                return [case.to_dict() for case in cases]
                
        except Exception as e:
            logger.error("Failed to search cases", 
                        query=query,
                        error=str(e))
            raise
    
    async def get_vehicles_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Get all vehicles for a specific case.
        
        Args:
            case_id: Case ID
            
        Returns:
            List of vehicles for the case
        """
        try:
            from ...database_service.app.repositories.vehicle_repository import VehicleRepository
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                vehicle_repo = VehicleRepository(db)
                vehicles = await vehicle_repo.get_by_case_id(case_id)
                
                return [vehicle.to_dict() for vehicle in vehicles]
                
        except Exception as e:
            logger.error("Failed to get vehicles by case", 
                        case_id=case_id,
                        error=str(e))
            raise
    
    async def update_vehicle_cvegs(self, 
                                 vehicle_id: str,
                                 cvegs_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update vehicle with new CVEGS matching results.
        
        Args:
            vehicle_id: Vehicle ID
            cvegs_result: New CVEGS matching result
            
        Returns:
            Updated vehicle record or None if not found
        """
        try:
            from ...database_service.app.repositories.vehicle_repository import VehicleRepository
            from ...database_service.app.config.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                vehicle_repo = VehicleRepository(db)
                vehicle = await vehicle_repo.update_cvegs_results(vehicle_id, cvegs_result)
                
                if vehicle:
                    logger.info("Vehicle CVEGS updated", 
                               vehicle_id=vehicle_id,
                               cvegs_code=vehicle.cvegs_code)
                    return vehicle.to_dict()
                
                return None
                
        except Exception as e:
            logger.error("Failed to update vehicle CVEGS", 
                        vehicle_id=vehicle_id,
                        error=str(e))
            raise
    
    async def check_health(self) -> bool:
        """
        Check if database service is healthy.
        
        Returns:
            True if service is healthy
        """
        try:
            from ...database_service.app.config.database import check_db_connection
            
            return await check_db_connection()
            
        except Exception as e:
            logger.error("Database health check error", error=str(e))
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for service requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{self.settings.app_name}/{self.settings.app_version}"
        }
        
        # Add internal API key if configured
        if self.settings.internal_api_key:
            headers["X-API-Key"] = self.settings.internal_api_key
        
        return headers
    
    async def bulk_create_attachments(self, 
                                    message_id: str,
                                    attachments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple attachment records in bulk.
        
        Args:
            message_id: Message ID (UUID)
            attachments_data: List of attachment data
            
        Returns:
            List of created attachment records
        """
        try:
            created_attachments = []
            
            for attachment_data in attachments_data:
                attachment_record = await self.create_attachment_record(
                    message_id=message_id,
                    attachment_info=attachment_data.get("info", {}),
                    storage_path=attachment_data.get("storage_path", ""),
                    processing_result=attachment_data.get("processing_result", {})
                )
                created_attachments.append(attachment_record)
            
            logger.info("Bulk attachments created", 
                       message_id=message_id,
                       attachment_count=len(created_attachments))
            
            return created_attachments
            
        except Exception as e:
            logger.error("Failed to bulk create attachments", 
                        message_id=message_id,
                        attachment_count=len(attachments_data),
                        error=str(e))
            raise
    
    async def get_recent_messages(self, 
                                limit: int = 50,
                                status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent messages with optional status filter.
        
        Args:
            limit: Maximum number of messages to return
            status: Optional status filter
            
        Returns:
            List of recent messages
        """
        try:
            from ...database_service.app.models.message import Message, MessageStatus
            from ...database_service.app.config.database import AsyncSessionLocal
            from sqlalchemy import select, desc
            
            async with AsyncSessionLocal() as db:
                query = select(Message).order_by(desc(Message.received_at)).limit(limit)
                
                if status:
                    query = query.where(Message.status == MessageStatus(status))
                
                result = await db.execute(query)
                messages = result.scalars().all()
                
                return [message.to_dict() for message in messages]
                
        except Exception as e:
            logger.error("Failed to get recent messages", 
                        limit=limit,
                        status=status,
                        error=str(e))
            raise
