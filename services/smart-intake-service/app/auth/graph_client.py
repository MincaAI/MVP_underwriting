import asyncio
from typing import Optional, Dict, List, Any
import httpx
import structlog
from msal import ConfidentialClientApplication
from datetime import datetime, timedelta
import json

from ..config.settings import get_settings, get_graph_authority_url

logger = structlog.get_logger()


class GraphTokenManager:
    """Manages Microsoft Graph API tokens with automatic refresh."""
    
    def __init__(self):
        self.settings = get_settings()
        self.authority = get_graph_authority_url()
        
        # Create MSAL client application
        self.app = ConfidentialClientApplication(
            client_id=self.settings.azure_client_id,
            client_credential=self.settings.azure_client_secret,
            authority=self.authority
        )
        
        # Token storage (in production, use Redis or database)
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    async def get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary.
        
        Returns:
            Valid access token
            
        Raises:
            Exception: If unable to get valid token
        """
        # Check if current token is still valid
        if self._is_token_valid():
            return self._access_token
        
        # Try to refresh token
        if self._refresh_token:
            try:
                await self._refresh_access_token()
                return self._access_token
            except Exception as e:
                logger.warning("Token refresh failed", error=str(e))
        
        # If refresh failed, need to re-authenticate
        raise Exception("No valid access token available. Re-authentication required.")
    
    def _is_token_valid(self) -> bool:
        """Check if current access token is valid."""
        if not self._access_token or not self._token_expires_at:
            return False
        
        # Check if token expires in next 5 minutes (buffer for safety)
        buffer_time = timedelta(minutes=5)
        return datetime.utcnow() + buffer_time < self._token_expires_at
    
    async def _refresh_access_token(self):
        """Refresh access token using refresh token."""
        try:
            result = self.app.acquire_token_by_refresh_token(
                refresh_token=self._refresh_token,
                scopes=self.settings.graph_scopes
            )
            
            if "access_token" in result:
                self._access_token = result["access_token"]
                self._refresh_token = result.get("refresh_token", self._refresh_token)
                
                # Calculate expiration time
                expires_in = result.get("expires_in", 3600)  # Default 1 hour
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                logger.info("Access token refreshed successfully")
            else:
                error = result.get("error_description", "Unknown error")
                raise Exception(f"Token refresh failed: {error}")
                
        except Exception as e:
            logger.error("Failed to refresh access token", error=str(e))
            raise
    
    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int = 3600):
        """
        Set tokens from OAuth callback.
        
        Args:
            access_token: Access token from OAuth flow
            refresh_token: Refresh token for token renewal
            expires_in: Token expiration time in seconds
        """
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        logger.info("Tokens set successfully", expires_at=self._token_expires_at)


class GraphAPIClient:
    """Microsoft Graph API client for email and attachment operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.token_manager = GraphTokenManager()
        self.base_url = self.settings.graph_api_base_url
        self.timeout = httpx.Timeout(30.0)
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Graph API calls."""
        access_token = await self.token_manager.get_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def get_message(self, message_id: str, expand_attachments: bool = True) -> Dict[str, Any]:
        """
        Get email message by ID.
        
        Args:
            message_id: Microsoft Graph message ID
            expand_attachments: Whether to include attachment details
            
        Returns:
            Message data from Graph API
        """
        try:
            headers = await self._get_headers()
            
            # Build URL with optional expansion
            url = f"{self.base_url}/me/messages/{message_id}"
            if expand_attachments:
                url += "?$expand=attachments"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                message_data = response.json()
                
                logger.info("Message retrieved successfully", 
                           message_id=message_id,
                           subject=message_data.get("subject", "")[:100])
                
                return message_data
                
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get message", 
                        message_id=message_id,
                        status_code=e.response.status_code,
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error getting message", 
                        message_id=message_id,
                        error=str(e))
            raise
    
    async def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """
        Download attachment content.
        
        Args:
            message_id: Microsoft Graph message ID
            attachment_id: Attachment ID
            
        Returns:
            Attachment content as bytes
        """
        try:
            headers = await self._get_headers()
            url = f"{self.base_url}/me/messages/{message_id}/attachments/{attachment_id}/$value"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                logger.info("Attachment downloaded", 
                           message_id=message_id,
                           attachment_id=attachment_id,
                           size_bytes=len(response.content))
                
                return response.content
                
        except httpx.HTTPStatusError as e:
            logger.error("Failed to download attachment", 
                        message_id=message_id,
                        attachment_id=attachment_id,
                        status_code=e.response.status_code,
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error downloading attachment", 
                        message_id=message_id,
                        attachment_id=attachment_id,
                        error=str(e))
            raise
    
    async def find_target_folder(self, folder_name: str = None) -> Optional[str]:
        """
        Find the target folder ID by name.
        
        Args:
            folder_name: Folder name to search for (defaults to settings)
            
        Returns:
            Folder ID if found, None otherwise
        """
        if folder_name is None:
            folder_name = self.settings.target_folder_name
        
        try:
            headers = await self._get_headers()
            url = f"{self.base_url}/me/mailFolders"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                folders = response.json().get("value", [])
                
                # Search for folder by name
                for folder in folders:
                    if folder.get("displayName") == folder_name:
                        folder_id = folder.get("id")
                        logger.info("Target folder found", 
                                   folder_name=folder_name,
                                   folder_id=folder_id)
                        return folder_id
                
                logger.warning("Target folder not found", folder_name=folder_name)
                return None
                
        except Exception as e:
            logger.error("Failed to find target folder", 
                        folder_name=folder_name,
                        error=str(e))
            raise
    
    async def create_subscription(self, folder_id: str) -> Dict[str, Any]:
        """
        Create Microsoft Graph subscription for email notifications.
        
        Args:
            folder_id: Folder ID to monitor
            
        Returns:
            Subscription details
        """
        try:
            headers = await self._get_headers()
            
            # Calculate expiration time (max 3 days for messages)
            expiration = datetime.utcnow() + timedelta(hours=self.settings.subscription_expiration_hours)
            
            subscription_data = {
                "changeType": "created,updated",
                "notificationUrl": get_webhook_notification_url(),
                "resource": f"/me/mailFolders/{folder_id}/messages",
                "expirationDateTime": expiration.isoformat() + "Z",
                "latestSupportedTlsVersion": "v1_2"
            }
            
            url = f"{self.base_url}/subscriptions"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=subscription_data)
                response.raise_for_status()
                
                subscription = response.json()
                
                logger.info("Subscription created successfully", 
                           subscription_id=subscription.get("id"),
                           folder_id=folder_id,
                           expiration=expiration)
                
                return subscription
                
        except httpx.HTTPStatusError as e:
            logger.error("Failed to create subscription", 
                        folder_id=folder_id,
                        status_code=e.response.status_code,
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error creating subscription", 
                        folder_id=folder_id,
                        error=str(e))
            raise
    
    async def renew_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Renew existing subscription before expiration.
        
        Args:
            subscription_id: Subscription ID to renew
            
        Returns:
            Updated subscription details
        """
        try:
            headers = await self._get_headers()
            
            # Calculate new expiration time
            expiration = datetime.utcnow() + timedelta(hours=self.settings.subscription_expiration_hours)
            
            update_data = {
                "expirationDateTime": expiration.isoformat() + "Z"
            }
            
            url = f"{self.base_url}/subscriptions/{subscription_id}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(url, headers=headers, json=update_data)
                response.raise_for_status()
                
                subscription = response.json()
                
                logger.info("Subscription renewed successfully", 
                           subscription_id=subscription_id,
                           new_expiration=expiration)
                
                return subscription
                
        except Exception as e:
            logger.error("Failed to renew subscription", 
                        subscription_id=subscription_id,
                        error=str(e))
            raise
    
    async def list_messages_in_folder(self, 
                                     folder_id: str, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """
        List messages in a specific folder.
        
        Args:
            folder_id: Folder ID to list messages from
            limit: Maximum number of messages to return
            
        Returns:
            List of message summaries
        """
        try:
            headers = await self._get_headers()
            url = f"{self.base_url}/me/mailFolders/{folder_id}/messages?$top={limit}&$orderby=receivedDateTime desc"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                messages = response.json().get("value", [])
                
                logger.info("Messages listed successfully", 
                           folder_id=folder_id,
                           message_count=len(messages))
                
                return messages
                
        except Exception as e:
            logger.error("Failed to list messages", 
                        folder_id=folder_id,
                        error=str(e))
            raise
