import asyncio
import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Callable, Optional
import logging
from datetime import datetime

from app.common.config import get_settings

logger = logging.getLogger(__name__)

class SQSConsumer:
    def __init__(self, queue_name: str, region: Optional[str] = None):
        self.settings = get_settings()
        self.queue_name = queue_name
        
        session = boto3.Session(
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=region or self.settings.s3_region,
        )
        
        self.sqs = session.client('sqs')
        self.queue_url = None
        
    async def _get_queue_url(self) -> str:
        """Get SQS queue URL"""
        if self.queue_url is None:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.sqs.get_queue_url(QueueName=self.queue_name)
                )
                self.queue_url = response['QueueUrl']
            except ClientError as e:
                logger.error(f"Failed to get queue URL for {self.queue_name}: {e}")
                raise
        
        return self.queue_url
    
    async def consume(
        self,
        handler: Callable[[Dict[str, Any]], None],
        max_messages: int = 10,
        wait_time: int = 20,
        visibility_timeout: int = 30
    ):
        """Consume messages from SQS queue"""
        queue_url = await self._get_queue_url()
        
        logger.info(f"Starting consumer for queue: {self.queue_name}")
        
        while True:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.sqs.receive_message(
                        QueueUrl=queue_url,
                        MaxNumberOfMessages=max_messages,
                        WaitTimeSeconds=wait_time,
                        VisibilityTimeoutSeconds=visibility_timeout,
                        AttributeNames=['All'],
                        MessageAttributeNames=['All']
                    )
                )
                
                messages = response.get('Messages', [])
                
                if not messages:
                    logger.debug("No messages received, continuing...")
                    continue
                
                # Process messages concurrently
                tasks = []
                for message in messages:
                    task = self._process_message(message, handler, queue_url)
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def _process_message(
        self,
        message: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], None],
        queue_url: str
    ):
        """Process a single SQS message"""
        receipt_handle = message['ReceiptHandle']
        message_id = message.get('MessageId', 'unknown')
        
        try:
            # Parse message body
            body = json.loads(message['Body'])
            
            # Add metadata
            body['_message_id'] = message_id
            body['_receipt_handle'] = receipt_handle
            body['_received_at'] = datetime.now().isoformat()
            
            logger.info(f"Processing message {message_id}")
            
            # Call handler
            await handler(body)
            
            # Delete message on success
            await self._delete_message(queue_url, receipt_handle)
            
            logger.info(f"Successfully processed message {message_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message {message_id}: {e}")
            await self._delete_message(queue_url, receipt_handle)  # Remove malformed message
            
        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")
            # Message will become visible again after visibility timeout
    
    async def _delete_message(self, queue_url: str, receipt_handle: str):
        """Delete processed message from queue"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
            )
        except ClientError as e:
            logger.error(f"Failed to delete message: {e}")

class SQSPublisher:
    def __init__(self, region: Optional[str] = None):
        self.settings = get_settings()
        
        session = boto3.Session(
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=region or self.settings.s3_region,
        )
        
        self.sqs = session.client('sqs')
        self._queue_urls = {}
    
    async def _get_queue_url(self, queue_name: str) -> str:
        """Get SQS queue URL with caching"""
        if queue_name not in self._queue_urls:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.sqs.get_queue_url(QueueName=queue_name)
                )
                self._queue_urls[queue_name] = response['QueueUrl']
            except ClientError as e:
                logger.error(f"Failed to get queue URL for {queue_name}: {e}")
                raise
        
        return self._queue_urls[queue_name]
    
    async def send_message(
        self,
        queue_name: str,
        message: Dict[str, Any],
        delay_seconds: int = 0,
        message_attributes: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> str:
        """Send message to SQS queue"""
        queue_url = await self._get_queue_url(queue_name)
        
        try:
            params = {
                'QueueUrl': queue_url,
                'MessageBody': json.dumps(message),
                'DelaySeconds': delay_seconds
            }
            
            if message_attributes:
                params['MessageAttributes'] = message_attributes
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.sqs.send_message(**params)
            )
            
            message_id = response['MessageId']
            logger.info(f"Sent message {message_id} to queue {queue_name}")
            
            return message_id
            
        except ClientError as e:
            logger.error(f"Failed to send message to {queue_name}: {e}")
            raise
    
    async def send_batch(
        self,
        queue_name: str,
        messages: list[Dict[str, Any]],
        max_batch_size: int = 10
    ) -> list[str]:
        """Send multiple messages in batches"""
        queue_url = await self._get_queue_url(queue_name)
        message_ids = []
        
        # Split into batches
        for i in range(0, len(messages), max_batch_size):
            batch = messages[i:i + max_batch_size]
            
            entries = []
            for idx, message in enumerate(batch):
                entries.append({
                    'Id': str(idx),
                    'MessageBody': json.dumps(message)
                })
            
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.sqs.send_message_batch(
                        QueueUrl=queue_url,
                        Entries=entries
                    )
                )
                
                # Extract message IDs
                for result in response.get('Successful', []):
                    message_ids.append(result['MessageId'])
                
                # Log any failures
                for failure in response.get('Failed', []):
                    logger.error(f"Failed to send message in batch: {failure}")
                
            except ClientError as e:
                logger.error(f"Failed to send batch to {queue_name}: {e}")
                raise
        
        logger.info(f"Sent {len(message_ids)} messages to queue {queue_name}")
        return message_ids

# Utility function to create message with idempotency
def create_idempotent_message(
    message_type: str,
    payload: Dict[str, Any],
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """Create message with idempotency key"""
    return {
        'message_type': message_type,
        'payload': payload,
        'idempotency_key': idempotency_key or f"{message_type}_{datetime.now().isoformat()}",
        'created_at': datetime.now().isoformat()
    }