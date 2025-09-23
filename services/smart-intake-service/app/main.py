# services/smart-intake-service/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
import structlog

from app.webhooks.graph_webhook import (
    get_webhook_handler,
    GraphNotification,
)
from app.tasks.email_tasks import (
    start_message_consumer,
    create_message_handler,
    get_queue_statistics,
    get_task_status
)

# Configure logging (stdlib + structlog to ensure logs appear in container)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = logging.getLogger(__name__)

# Global variable to track consumer task
_consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    global _consumer_task

    # Startup
    logger.info("Starting Smart Intake Service...")

    # Start MQ consumer in background
    try:
        message_handler = create_message_handler()
        _consumer_task = asyncio.create_task(
            start_message_consumer("mvp-underwriting-pre-analysis", message_handler)
        )
        logger.info("MQ consumer started successfully")
    except Exception as e:
        logger.error(f"Failed to start MQ consumer: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Smart Intake Service...")
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        logger.info("MQ consumer stopped")


app = FastAPI(
    title="Smart Intake Service",
    lifespan=lifespan
)

handler = get_webhook_handler()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "ok": True,
        "service": "smart-intake-service",
        "queue_stats": get_queue_statistics()
    }


@app.get("/tasks/{task_id}/status")
async def get_task_status_endpoint(task_id: str):
    """Get status of a specific task."""
    return get_task_status(task_id)


# Microsoft Graph validation ping (?validationToken=...)
@app.get("/graph/notifications")
async def graph_validation(validationToken: str | None = None):
    return await handler.handle_validation(validationToken)


# Microsoft Graph notifications
@app.post("/graph/notifications")
async def graph_notifications(notification: GraphNotification, request: Request):
    payload = await request.body()
    if not handler.validate_webhook_signature(request, payload):
        raise HTTPException(status_code=401, detail="Invalid signature")
    return await handler.handle_notification(notification, request)
