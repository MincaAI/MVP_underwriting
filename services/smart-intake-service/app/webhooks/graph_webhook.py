from typing import List, Dict, Any, Optional
from fastapi import Request, HTTPException
from pydantic import BaseModel, Field
import structlog
import hmac
import hashlib
import base64
from datetime import datetime

from ..config.settings import get_settings
from ..tasks.email_tasks import process_email_task

logger = structlog.get_logger()


class GraphNotificationValue(BaseModel):
    """Individual notification from Microsoft Graph."""
    
    subscriptionId: str = Field(..., description="Subscription ID")
    subscriptionExpirationDateTime: str = Field(..., description="Subscription expiration")
    changeType: str = Field(..., description="Type of change (created, updated)")
    resource: str = Field(..., description="Resource path")
    resourceData: Dict[str, Any] = Field(..., description="Resource data")
    clientState: Optional[str] = Field(None, description="Client state")
    tenantId: str = Field(..., description="Tenant ID")


class GraphNotification(BaseModel):
    """Microsoft Graph webhook notification payload."""
    
    value: List[GraphNotificationValue] = Field(..., description="List of notifications")


class GraphWebhookHandler:
    """Handles Microsoft Graph webhook notifications."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def validate_webhook_signature(self, request: Request, payload: bytes) -> bool:
        """
        Validate webhook signature for security.
        
        Args:
            request: FastAPI request object
            payload: Raw request payload
            
        Returns:
            True if signature is valid
        """
        if not self.settings.webhook_secret:
            logger.warning("Webhook secret not configured, skipping signature validation")
            return True
        
        try:
            # Get signature from headers
            signature_header = request.headers.get("X-Hub-Signature-256")
            if not signature_header:
                logger.error("Missing webhook signature header")
                return False
            
            # Extract signature
            if not signature_header.startswith("sha256="):
                logger.error("Invalid signature format")
                return False
            
            received_signature = signature_header[7:]  # Remove "sha256=" prefix
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.settings.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            is_valid = hmac.compare_digest(received_signature, expected_signature)
            
            if not is_valid:
                logger.error("Webhook signature validation failed")
            
            return is_valid
            
        except Exception as e:
            logger.error("Error validating webhook signature", error=str(e))
            return False
    
    async def handle_validation(self, validation_token: Optional[str] = None) -> str:
        """
        Handle Microsoft Graph webhook validation.
        
        Args:
            validation_token: Validation token from Graph
            
        Returns:
            Validation token to confirm webhook endpoint
        """
        logger.info("Webhook validation requested", 
                   validation_token=validation_token[:20] + "..." if validation_token else None)
        
        # Return the validation token to confirm the endpoint
        return validation_token or "ok"
    
    async def handle_notification(self, 
                                notification: GraphNotification,
                                request: Request) -> Dict[str, Any]:
        """
        Handle incoming Microsoft Graph notifications.
        
        Args:
            notification: Parsed notification payload
            request: FastAPI request object
            
        Returns:
            Response indicating processing status
        """
        try:
            logger.info("Graph notification received", 
                       notification_count=len(notification.value))
            
            processed_count = 0
            queued_count = 0
            error_count = 0
            
            for notification_value in notification.value:
                try:
                    # Extract message ID from resource data
                    message_id = notification_value.resourceData.get("id")
                    if not message_id:
                        logger.warning("No message ID in notification", 
                                     resource_data=notification_value.resourceData)
                        error_count += 1
                        continue
                    
                    # Log notification details
                    logger.info("Processing notification", 
                               message_id=message_id,
                               change_type=notification_value.changeType,
                               subscription_id=notification_value.subscriptionId)
                    
                    # Queue email processing task
                    task_result = process_email_task.delay(
                        message_id=message_id,
                        change_type=notification_value.changeType,
                        subscription_id=notification_value.subscriptionId
                    )
                    
                    logger.info("Email processing task queued", 
                               message_id=message_id,
                               task_id=task_result.id)
                    
                    queued_count += 1
                    
                except Exception as e:
                    logger.error("Failed to process notification", 
                               notification_data=notification_value.dict(),
                               error=str(e))
                    error_count += 1
            
            processed_count = queued_count  # All queued notifications are considered processed
            
            response = {
                "received": True,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_notifications": len(notification.value),
                    "processed": processed_count,
                    "queued": queued_count,
                    "errors": error_count
                }
            }
            
            logger.info("Graph notification processing completed", 
                       summary=response["summary"])
            
            return response
            
        except Exception as e:
            logger.error("Failed to handle Graph notification", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to process notification")
    
    async def handle_subscription_expiration(self, subscription_id: str) -> bool:
        """
        Handle subscription expiration by renewing it.
        
        Args:
            subscription_id: Subscription ID to renew
            
        Returns:
            True if renewal was successful
        """
        try:
            from ..auth.graph_client import GraphAPIClient
            
            graph_client = GraphAPIClient()
            renewed_subscription = await graph_client.renew_subscription(subscription_id)
            
            logger.info("Subscription renewed due to expiration", 
                       subscription_id=subscription_id,
                       new_expiration=renewed_subscription.get("expirationDateTime"))
            
            return True
            
        except Exception as e:
            logger.error("Failed to renew expired subscription", 
                        subscription_id=subscription_id,
                        error=str(e))
            return False
    
    def extract_message_metadata(self, notification_value: GraphNotificationValue) -> Dict[str, Any]:
        """
        Extract useful metadata from notification.
        
        Args:
            notification_value: Graph notification value
            
        Returns:
            Extracted metadata
        """
        resource_data = notification_value.resourceData
        
        return {
            "message_id": resource_data.get("id"),
            "change_type": notification_value.changeType,
            "subscription_id": notification_value.subscriptionId,
            "tenant_id": notification_value.tenantId,
            "resource_path": notification_value.resource,
            "received_at": datetime.utcnow().isoformat(),
            "client_state": notification_value.clientState
        }
    
    async def get_notification_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about webhook notifications.
        
        Returns:
            Notification statistics
        """
        # In production, this would query a database or metrics store
        # For now, return basic information
        return {
            "webhook_endpoint": get_webhook_notification_url(),
            "validation_endpoint": f"{get_webhook_notification_url()}?validationToken={{token}}",
            "supported_change_types": ["created", "updated"],
            "max_notification_batch_size": 100,
            "processing_timeout": self.settings.email_processing_timeout,
            "last_updated": datetime.utcnow().isoformat()
        }


# Global webhook handler instance
webhook_handler = GraphWebhookHandler()


def get_webhook_handler() -> GraphWebhookHandler:
    """Get webhook handler instance."""
    return webhook_handler
