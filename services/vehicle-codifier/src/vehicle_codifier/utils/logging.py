import logging
import sys
from typing import Dict, Any
import structlog
from pythonjsonlogger import jsonlogger

from ..config.settings import get_settings


def setup_logging() -> None:
    """Setup structured logging configuration."""
    settings = get_settings()
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    # Configure structlog
    if settings.log_format.lower() == "json":
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class RequestLogger:
    """Logger for HTTP requests with structured context."""
    
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def log_request(self, 
                   method: str, 
                   path: str, 
                   request_id: str,
                   user_agent: str = None,
                   ip_address: str = None) -> None:
        """Log incoming HTTP request."""
        self.logger.info(
            "HTTP request received",
            method=method,
            path=path,
            request_id=request_id,
            user_agent=user_agent,
            ip_address=ip_address
        )
    
    def log_response(self,
                    method: str,
                    path: str,
                    request_id: str,
                    status_code: int,
                    processing_time_ms: float) -> None:
        """Log HTTP response."""
        self.logger.info(
            "HTTP response sent",
            method=method,
            path=path,
            request_id=request_id,
            status_code=status_code,
            processing_time_ms=processing_time_ms
        )


class MatchingLogger:
    """Logger for vehicle matching operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def log_match_start(self, 
                       description: str, 
                       insurer_id: str,
                       request_id: str = None) -> None:
        """Log start of matching operation."""
        self.logger.info(
            "Vehicle matching started",
            description=description[:100] + "..." if len(description) > 100 else description,
            insurer_id=insurer_id,
            request_id=request_id
        )
    
    def log_match_result(self,
                        description: str,
                        cvegs_code: str,
                        confidence_score: float,
                        processing_time_ms: float,
                        candidates_evaluated: int,
                        match_method: str,
                        request_id: str = None) -> None:
        """Log matching result."""
        self.logger.info(
            "Vehicle matching completed",
            description=description[:100] + "..." if len(description) > 100 else description,
            cvegs_code=cvegs_code,
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms,
            candidates_evaluated=candidates_evaluated,
            match_method=match_method,
            request_id=request_id
        )
    
    def log_match_error(self,
                       description: str,
                       error: str,
                       processing_time_ms: float = None,
                       request_id: str = None) -> None:
        """Log matching error."""
        self.logger.error(
            "Vehicle matching failed",
            description=description[:100] + "..." if len(description) > 100 else description,
            error=error,
            processing_time_ms=processing_time_ms,
            request_id=request_id
        )
    
    def log_batch_start(self,
                       vehicle_count: int,
                       insurer_id: str,
                       parallel_processing: bool,
                       request_id: str = None) -> None:
        """Log start of batch matching."""
        self.logger.info(
            "Batch matching started",
            vehicle_count=vehicle_count,
            insurer_id=insurer_id,
            parallel_processing=parallel_processing,
            request_id=request_id
        )
    
    def log_batch_result(self,
                        vehicle_count: int,
                        successful_matches: int,
                        failed_matches: int,
                        total_processing_time_ms: float,
                        success_rate: float,
                        request_id: str = None) -> None:
        """Log batch matching result."""
        self.logger.info(
            "Batch matching completed",
            vehicle_count=vehicle_count,
            successful_matches=successful_matches,
            failed_matches=failed_matches,
            total_processing_time_ms=total_processing_time_ms,
            success_rate=success_rate,
            avg_processing_time_ms=total_processing_time_ms / vehicle_count if vehicle_count > 0 else 0,
            request_id=request_id
        )


class DataLogger:
    """Logger for data operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def log_dataset_load_start(self, 
                              insurer_id: str, 
                              dataset_path: str) -> None:
        """Log start of dataset loading."""
        self.logger.info(
            "Dataset loading started",
            insurer_id=insurer_id,
            dataset_path=dataset_path
        )
    
    def log_dataset_load_success(self,
                                insurer_id: str,
                                records_count: int,
                                brands_count: int,
                                models_count: int,
                                load_time_ms: float) -> None:
        """Log successful dataset loading."""
        self.logger.info(
            "Dataset loaded successfully",
            insurer_id=insurer_id,
            records_count=records_count,
            brands_count=brands_count,
            models_count=models_count,
            load_time_ms=load_time_ms
        )
    
    def log_dataset_load_error(self,
                              insurer_id: str,
                              dataset_path: str,
                              error: str) -> None:
        """Log dataset loading error."""
        self.logger.error(
            "Dataset loading failed",
            insurer_id=insurer_id,
            dataset_path=dataset_path,
            error=error
        )
    
    def log_cache_hit(self, insurer_id: str, cache_path: str) -> None:
        """Log cache hit."""
        self.logger.debug(
            "Dataset cache hit",
            insurer_id=insurer_id,
            cache_path=cache_path
        )
    
    def log_cache_miss(self, insurer_id: str, cache_path: str) -> None:
        """Log cache miss."""
        self.logger.debug(
            "Dataset cache miss",
            insurer_id=insurer_id,
            cache_path=cache_path
        )


class LLMLogger:
    """Logger for LLM operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def log_llm_request(self,
                       description: str,
                       model: str,
                       request_type: str = "extraction") -> None:
        """Log LLM API request."""
        self.logger.debug(
            "LLM request sent",
            description=description[:100] + "..." if len(description) > 100 else description,
            model=model,
            request_type=request_type
        )
    
    def log_llm_response(self,
                        description: str,
                        model: str,
                        response_time_ms: float,
                        tokens_used: int = None,
                        request_type: str = "extraction") -> None:
        """Log LLM API response."""
        self.logger.debug(
            "LLM response received",
            description=description[:100] + "..." if len(description) > 100 else description,
            model=model,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            request_type=request_type
        )
    
    def log_llm_error(self,
                     description: str,
                     model: str,
                     error: str,
                     request_type: str = "extraction") -> None:
        """Log LLM API error."""
        self.logger.error(
            "LLM request failed",
            description=description[:100] + "..." if len(description) > 100 else description,
            model=model,
            error=error,
            request_type=request_type
        )
    
    def log_rate_limit(self, model: str, retry_after: int = None) -> None:
        """Log rate limit hit."""
        self.logger.warning(
            "LLM rate limit hit",
            model=model,
            retry_after=retry_after
        )


# Global logger instances
request_logger = RequestLogger()
matching_logger = MatchingLogger()
data_logger = DataLogger()
llm_logger = LLMLogger()
