#!/usr/bin/env python3
"""
Queue factory to create appropriate queue implementations based on environment.
Supports both local development (in-memory) and production (SQS).
"""

import os
import logging
from typing import Dict, Any, Callable, Optional
from .local_queue import local_queue
from .consumer import SQSConsumer, SQSPublisher

logger = logging.getLogger(__name__)

class QueueFactory:
    """Factory to create appropriate queue based on environment"""
    
    @staticmethod
    def get_publisher():
        """Get message publisher"""
        backend = os.getenv("QUEUE_BACKEND", "local")
        logger.info(f"Creating publisher with backend: {backend}")
        
        if backend == "local":
            return LocalPublisher()
        else:
            return SQSPublisher()
    
    @staticmethod
    def get_consumer(queue_name: str):
        """Get message consumer"""
        backend = os.getenv("QUEUE_BACKEND", "local")
        logger.info(f"Creating consumer for queue {queue_name} with backend: {backend}")
        
        if backend == "local":
            return LocalConsumer(queue_name)
        else:
            return SQSConsumer(queue_name)

class LocalPublisher:
    """Local message publisher using in-memory queue"""
    
    async def send_message(
        self, 
        queue_name: str, 
        message: Dict[str, Any],
        delay_seconds: int = 0,
        message_attributes: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> str:
        """Send message to local queue"""
        return await local_queue.send_message(queue_name, message, delay_seconds)
    
    async def send_batch(
        self, 
        queue_name: str, 
        messages: list[Dict[str, Any]],
        max_batch_size: int = 10
    ) -> list[str]:
        """Send batch of messages to local queue"""
        message_ids = []
        for message in messages[:max_batch_size]:
            message_id = await self.send_message(queue_name, message)
            message_ids.append(message_id)
        return message_ids

class LocalConsumer:
    """Local message consumer using in-memory queue"""
    
    def __init__(self, queue_name: str, region: Optional[str] = None):
        self.queue_name = queue_name
        self.region = region
    
    async def consume(
        self, 
        handler: Callable[[Dict[str, Any]], None],
        max_messages: int = 10,
        wait_time: int = 20,
        visibility_timeout: int = 30
    ):
        """Consume messages from local queue"""
        await local_queue.consume(
            self.queue_name, 
            handler, 
            max_messages, 
            wait_time, 
            visibility_timeout
        )
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return local_queue.get_queue_stats(self.queue_name)
    
    def clear_queue(self):
        """Clear queue (for testing)"""
        local_queue.clear_queue(self.queue_name)
