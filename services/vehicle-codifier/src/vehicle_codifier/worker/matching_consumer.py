#!/usr/bin/env python3
"""
Vehicle matching consumer that processes matching requests from the preprocessing pipeline.
"""

import asyncio
import logging
import sys
import pathlib
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add packages to path for local development
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "db" / "src"))
sys.path.insert(0, str(project_root / "packages" / "mq" / "src"))
sys.path.insert(0, str(current_dir.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variable overrides for local development
if not os.getenv("DOCKER_CONTAINER"):
    # Override for local development
    if "db:5432" in os.getenv("DATABASE_URL", ""):
        os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "").replace("db:5432", "localhost:5432")

from app.mq.queue_factory import QueueFactory
from services.matching_service import VehicleMatchingService

class VehicleMatchingConsumer:
    """Consumer for vehicle matching requests"""
    
    def __init__(self):
        self.matching_service = VehicleMatchingService()
    
    async def handle_matching_message(self, message: Dict[str, Any]):
        """Handle vehicle matching messages"""
        try:
            payload = message["payload"]
            run_id = payload["run_id"]
            case_id = payload["case_id"]
            
            logger.info(f"Processing vehicle matching request for run {run_id}")
            
            # Process the matching request
            await self.matching_service.process_matching_request(run_id, case_id)
            
        except Exception as e:
            logger.error(f"Error processing matching message: {e}")
            # Could implement retry logic here

async def main():
    """Main consumer loop for vehicle matching"""
    logger.info("🚀 Starting Vehicle Matching Consumer...")
    logger.info(f"📁 Working directory: {pathlib.Path.cwd()}")
    logger.info(f"🔗 Database URL: {os.getenv('DATABASE_URL', 'Not set')}")
    logger.info(f"📦 Queue Backend: {os.getenv('QUEUE_BACKEND', 'local')}")
    logger.info()
    
    # Create consumer instance
    consumer = VehicleMatchingConsumer()
    
    # Create queue consumer for matching requests
    matching_consumer = QueueFactory.get_consumer("mvp-underwriting-matching")
    
    logger.info("📋 Starting consumer for matching queue:")
    logger.info("  - mvp-underwriting-matching (Vehicle matching against AMIS catalog)")
    logger.info()
    
    try:
        # Run matching consumer
        await matching_consumer.consume(consumer.handle_matching_message)
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"❌ Error in consumer loop: {e}")
        raise
    finally:
        logger.info("👋 Vehicle Matching Consumer stopped")

if __name__ == "__main__":
    # Check if running from correct directory
    current_dir = pathlib.Path.cwd()
    if not (current_dir / "services" / "vehicle-codifier").exists() and not current_dir.name == "vehicle-codifier":
        print("❌ Please run this script from the project root directory or vehicle-codifier directory")
        sys.exit(1)
    
    asyncio.run(main())
