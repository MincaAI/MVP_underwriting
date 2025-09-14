#!/usr/bin/env python3
"""
Local in-memory queue implementation for development.
This provides a simple queue interface without external dependencies.
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from collections import defaultdict, deque
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class LocalQueue:
    """In-memory queue for local development"""
    
    def __init__(self):
        self.queues = defaultdict(deque)
        self.consumers = defaultdict(list)
        self.running = False
        self.message_history = defaultdict(list)  # For debugging
    
    async def send_message(
        self, 
        queue_name: str, 
        message: Dict[str, Any],
        delay_seconds: int = 0
    ) -> str:
        """Send message to local queue"""
        message_id = str(uuid.uuid4())
        message['_message_id'] = message_id
        message['_sent_at'] = datetime.now().isoformat()
        
        if delay_seconds > 0:
            # For delayed messages, we'll process them after delay
            asyncio.create_task(self._delayed_send(queue_name, message, delay_seconds))
        else:
            self.queues[queue_name].append(message)
            logger.info(f"Sent message {message_id} to local queue {queue_name}")
            
            # Process immediately if consumer is waiting
            if self.consumers[queue_name]:
                await self._process_messages(queue_name)
        
        return message_id
    
    async def _delayed_send(self, queue_name: str, message: Dict[str, Any], delay_seconds: int):
        """Send delayed message"""
        await asyncio.sleep(delay_seconds)
        self.queues[queue_name].append(message)
        logger.info(f"Sent delayed message {message['_message_id']} to local queue {queue_name}")
        
        if self.consumers[queue_name]:
            await self._process_messages(queue_name)
    
    async def consume(
        self, 
        queue_name: str, 
        handler: Callable[[Dict[str, Any]], None],
        max_messages: int = 10,
        wait_time: int = 20,
        visibility_timeout: int = 30
    ):
        """Consume messages from local queue"""
        self.consumers[queue_name].append(handler)
        logger.info(f"Started consumer for local queue {queue_name}")
        
        # Process any existing messages
        await self._process_messages(queue_name)
        
        # Keep consumer alive
        while True:
            await asyncio.sleep(1)
            if self.queues[queue_name]:
                await self._process_messages(queue_name)
    
    async def _process_messages(self, queue_name: str):
        """Process messages in queue"""
        processed_count = 0
        max_batch = 10  # Process up to 10 messages at once
        
        while (self.queues[queue_name] and 
               self.consumers[queue_name] and 
               processed_count < max_batch):
            
            message = self.queues[queue_name].popleft()
            handler = self.consumers[queue_name][0]
            
            try:
                logger.info(f"Processing message {message.get('_message_id', 'unknown')}")
                await handler(message)
                processed_count += 1
                
                # Store in history for debugging
                self.message_history[queue_name].append({
                    'message': message,
                    'processed_at': datetime.now().isoformat(),
                    'status': 'success'
                })
                
            except Exception as e:
                logger.error(f"Error processing message {message.get('_message_id', 'unknown')}: {e}")
                
                # Store error in history
                self.message_history[queue_name].append({
                    'message': message,
                    'processed_at': datetime.now().isoformat(),
                    'status': 'error',
                    'error': str(e)
                })
                
                # Re-queue message for retry (simple retry logic)
                if message.get('_retry_count', 0) < 3:
                    message['_retry_count'] = message.get('_retry_count', 0) + 1
                    self.queues[queue_name].appendleft(message)
                    logger.info(f"Re-queued message for retry {message['_retry_count']}/3")
                else:
                    logger.error(f"Message failed after 3 retries, discarding")
                
                break
    
    def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get queue statistics for monitoring"""
        return {
            'queue_name': queue_name,
            'pending_messages': len(self.queues[queue_name]),
            'active_consumers': len(self.consumers[queue_name]),
            'total_processed': len([h for h in self.message_history[queue_name] if h['status'] == 'success']),
            'total_errors': len([h for h in self.message_history[queue_name] if h['status'] == 'error'])
        }
    
    def clear_queue(self, queue_name: str):
        """Clear all messages from queue (for testing)"""
        self.queues[queue_name].clear()
        self.message_history[queue_name].clear()
        logger.info(f"Cleared queue {queue_name}")

# Global instance
local_queue = LocalQueue()
