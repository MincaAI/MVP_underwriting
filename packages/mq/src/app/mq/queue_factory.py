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
from .config import get_queue_config, QueueNames, is_local_environment, is_sqs_environment

logger = logging.getLogger(__name__)

class QueueFactory:
    """Factory to create appropriate queue based on environment"""
    
    @staticmethod
    def get_publisher():
        """Get message publisher"""
        config = get_queue_config()
        backend = config.get_backend()
        logger.info(f"Creating publisher with backend: {backend} (environment: {config.environment})")
        
        if backend == "local":
            return LocalPublisher()
        else:
            return SQSPublisher(region=config.get_region())
    
    @staticmethod
    def get_consumer(queue_name: str):
        """Get message consumer"""
        config = get_queue_config()
        backend = config.get_backend()
        
        # Get the full queue name with environment prefix
        full_queue_name = config.get_queue_name(queue_name)
        
        logger.info(f"Creating consumer for queue {full_queue_name} with backend: {backend} (environment: {config.environment})")
        
        if backend == "local":
            return LocalConsumer(full_queue_name, config=config)
        else:
            return SQSConsumer(full_queue_name, region=config.get_region(), config=config)
    
    @staticmethod
    def get_queue_name(base_name: str) -> str:
        """Get the full queue name with environment prefix"""
        config = get_queue_config()
        return config.get_queue_name(base_name)
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get current queue configuration"""
        config = get_queue_config()
        return config.to_dict()
    
    @staticmethod
    def list_all_queues() -> Dict[str, str]:
        """List all available queues with their full names"""
        config = get_queue_config()
        return config.get_all_queue_names()

class LocalPublisher:
    """Local message publisher using in-memory queue"""
    
    def __init__(self, config=None):
        """Initialize local publisher with configuration."""
        self.config = config or get_queue_config()
    
    async def send_message(
        self, 
        queue_name: str, 
        message: Dict[str, Any],
        delay_seconds: int = 0,
        message_attributes: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> str:
        """Send message to local queue"""
        # Use the full queue name (already has prefix if needed)
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
    
    def __init__(self, queue_name: str, region: Optional[str] = None, config=None):
        """Initialize local consumer with configuration."""
        self.queue_name = queue_name
        self.region = region
        self.config = config or get_queue_config()
    
    async def consume(
        self, 
        handler: Callable[[Dict[str, Any]], None],
        max_messages: int = 10,
        wait_time: int = 20,
        visibility_timeout: int = 30
    ):
        """Consume messages from local queue"""
        # Use configuration defaults if not specified
        if visibility_timeout == 30:  # Default value
            visibility_timeout = self.config.get_visibility_timeout()
        
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
