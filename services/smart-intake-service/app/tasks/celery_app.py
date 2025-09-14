from celery import Celery
import structlog
from ..config.settings import get_celery_settings

logger = structlog.get_logger()

# Get Celery settings
celery_settings = get_celery_settings()

# Create Celery app
celery_app = Celery(
    "smart_intake",
    broker=celery_settings.broker_url,
    backend=celery_settings.result_backend,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.document_tasks"
    ]
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer=celery_settings.task_serializer,
    result_serializer=celery_settings.result_serializer,
    accept_content=celery_settings.accept_content,
    
    # Timezone
    timezone=celery_settings.timezone,
    enable_utc=celery_settings.enable_utc,
    
    # Worker settings
    worker_prefetch_multiplier=celery_settings.worker_prefetch_multiplier,
    task_acks_late=celery_settings.task_acks_late,
    worker_max_tasks_per_child=celery_settings.worker_max_tasks_per_child,
    
    # Task routing
    task_routes=celery_settings.task_routes,
    
    # Time limits
    task_soft_time_limit=celery_settings.task_soft_time_limit,
    task_time_limit=celery_settings.task_time_limit,
    
    # Retry settings
    task_default_retry_delay=celery_settings.task_default_retry_delay,
    task_max_retries=celery_settings.task_max_retries,
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Configure structured logging for Celery
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    logger.info("Debug task executed", task_id=self.request.id)
    return f"Debug task completed: {self.request.id}"


# Task status tracking
class TaskStatus:
    """Track task execution status and metrics."""
    
    @staticmethod
    def log_task_start(task_name: str, task_id: str, **kwargs):
        """Log task start with context."""
        logger.info("Task started", 
                   task_name=task_name,
                   task_id=task_id,
                   **kwargs)
    
    @staticmethod
    def log_task_success(task_name: str, task_id: str, duration: float, **kwargs):
        """Log successful task completion."""
        logger.info("Task completed successfully", 
                   task_name=task_name,
                   task_id=task_id,
                   duration_seconds=duration,
                   **kwargs)
    
    @staticmethod
    def log_task_failure(task_name: str, task_id: str, error: str, **kwargs):
        """Log task failure."""
        logger.error("Task failed", 
                    task_name=task_name,
                    task_id=task_id,
                    error=error,
                    **kwargs)
    
    @staticmethod
    def log_task_retry(task_name: str, task_id: str, attempt: int, error: str, **kwargs):
        """Log task retry attempt."""
        logger.warning("Task retry", 
                      task_name=task_name,
                      task_id=task_id,
                      attempt=attempt,
                      error=error,
                      **kwargs)


# Celery signal handlers for monitoring
@celery_app.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run signal."""
    TaskStatus.log_task_start(
        task_name=task.name if task else "unknown",
        task_id=task_id,
        args_count=len(args) if args else 0,
        kwargs_keys=list(kwargs.keys()) if kwargs else []
    )


@celery_app.task_success.connect
def task_success_handler(sender=None, task_id=None, result=None, runtime=None, **kwds):
    """Handle task success signal."""
    TaskStatus.log_task_success(
        task_name=sender.name if sender else "unknown",
        task_id=task_id,
        duration=runtime,
        result_type=type(result).__name__ if result else "None"
    )


@celery_app.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure signal."""
    TaskStatus.log_task_failure(
        task_name=sender.name if sender else "unknown",
        task_id=task_id,
        error=str(exception) if exception else "Unknown error"
    )


@celery_app.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Handle task retry signal."""
    TaskStatus.log_task_retry(
        task_name=sender.name if sender else "unknown",
        task_id=task_id,
        attempt=sender.request.retries + 1 if sender and sender.request else 0,
        error=str(reason) if reason else "Unknown error"
    )


# Health check for Celery
def check_celery_health() -> Dict[str, Any]:
    """
    Check Celery worker health.
    
    Returns:
        Health status information
    """
    try:
        # Check if workers are available
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active_workers = len(stats) if stats else 0
        
        # Check broker connection
        broker_healthy = True
        try:
            celery_app.broker_connection().ensure_connection(max_retries=1)
        except Exception:
            broker_healthy = False
        
        return {
            "celery_healthy": active_workers > 0 and broker_healthy,
            "active_workers": active_workers,
            "broker_connected": broker_healthy,
            "queues": list(celery_settings.task_routes.values()) if hasattr(celery_settings, 'task_routes') else [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to check Celery health", error=str(e))
        return {
            "celery_healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Export the Celery app
__all__ = ["celery_app", "TaskStatus", "check_celery_health"]
