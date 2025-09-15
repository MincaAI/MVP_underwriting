#!/usr/bin/env python3
"""
Queue configuration management for environment-aware queue setup.
Supports local development, staging, and production environments.
"""

import os
from typing import Dict, Any, Optional
from enum import Enum


class QueueEnvironment(str, Enum):
    """Supported queue environments."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class QueueNames:
    """Centralized queue name definitions."""
    # Pre-analysis queue for initial email processing
    PRE_ANALYSIS = "mvp-underwriting-pre-analysis"
    
    # Main processing queues
    EXTRACT = "mvp-underwriting-extract"
    TRANSFORM = "mvp-underwriting-transform"
    EXPORT = "mvp-underwriting-export"
    MATCHING = "mvp-underwriting-matching"
    
    # Dead letter queues
    PRE_ANALYSIS_DLQ = "mvp-underwriting-pre-analysis-dlq"
    EXTRACT_DLQ = "mvp-underwriting-extract-dlq"
    TRANSFORM_DLQ = "mvp-underwriting-transform-dlq"
    EXPORT_DLQ = "mvp-underwriting-export-dlq"
    MATCHING_DLQ = "mvp-underwriting-matching-dlq"
    
    @classmethod
    def get_all_queues(cls) -> list[str]:
        """Get all queue names."""
        return [
            cls.PRE_ANALYSIS, cls.EXTRACT, cls.TRANSFORM, cls.EXPORT, cls.MATCHING,
            cls.PRE_ANALYSIS_DLQ, cls.EXTRACT_DLQ, cls.TRANSFORM_DLQ, cls.EXPORT_DLQ, cls.MATCHING_DLQ
        ]
    
    @classmethod
    def get_main_queues(cls) -> list[str]:
        """Get main processing queue names (excluding DLQ)."""
        return [cls.PRE_ANALYSIS, cls.EXTRACT, cls.TRANSFORM, cls.EXPORT, cls.MATCHING]


class QueueConfig:
    """Queue configuration management."""
    
    # Environment-specific settings
    ENVIRONMENTS = {
        QueueEnvironment.LOCAL: {
            "backend": "local",
            "prefix": "",
            "region": None,
            "debug": True,
            "persistence": False,  # In-memory only for local
            "retry_attempts": 3,
            "visibility_timeout": 30,
            "message_retention": 3600  # 1 hour for local testing
        },
        QueueEnvironment.DEVELOPMENT: {
            "backend": "sqs",
            "prefix": "dev-",
            "region": "us-east-1",
            "debug": True,
            "persistence": True,
            "retry_attempts": 3,
            "visibility_timeout": 60,
            "message_retention": 86400  # 1 day
        },
        QueueEnvironment.STAGING: {
            "backend": "sqs",
            "prefix": "staging-",
            "region": "us-east-1",
            "debug": False,
            "persistence": True,
            "retry_attempts": 5,
            "visibility_timeout": 120,
            "message_retention": 259200  # 3 days
        },
        QueueEnvironment.PRODUCTION: {
            "backend": "sqs",
            "prefix": "prod-",
            "region": "us-east-1",
            "debug": False,
            "persistence": True,
            "retry_attempts": 5,
            "visibility_timeout": 300,  # 5 minutes
            "message_retention": 1209600  # 14 days (SQS maximum)
        }
    }
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize queue configuration.
        
        Args:
            environment: Environment name (local, development, staging, production)
        """
        self.environment = environment or os.getenv("ENVIRONMENT", QueueEnvironment.LOCAL)
        self.config = self._load_environment_config()
    
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration for the current environment."""
        if self.environment not in self.ENVIRONMENTS:
            raise ValueError(f"Unknown environment: {self.environment}. "
                           f"Supported: {list(self.ENVIRONMENTS.keys())}")
        
        return self.ENVIRONMENTS[self.environment].copy()
    
    def get_queue_name(self, base_name: str) -> str:
        """
        Get the full queue name with environment prefix.
        
        Args:
            base_name: Base queue name (e.g., 'mvp-underwriting-extract')
            
        Returns:
            Full queue name with prefix (e.g., 'dev-mvp-underwriting-extract')
        """
        prefix = self.config.get("prefix", "")
        return f"{prefix}{base_name}"
    
    def get_all_queue_names(self) -> Dict[str, str]:
        """
        Get all queue names with environment prefixes.
        
        Returns:
            Dictionary mapping base names to full names
        """
        return {
            base_name: self.get_queue_name(base_name)
            for base_name in QueueNames.get_all_queues()
        }
    
    def get_backend(self) -> str:
        """Get the queue backend type (local or sqs)."""
        return self.config["backend"]
    
    def get_region(self) -> Optional[str]:
        """Get the AWS region for SQS queues."""
        return self.config.get("region")
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.config.get("debug", False)
    
    def get_retry_attempts(self) -> int:
        """Get the number of retry attempts for failed messages."""
        return self.config.get("retry_attempts", 3)
    
    def get_visibility_timeout(self) -> int:
        """Get the visibility timeout for messages in seconds."""
        return self.config.get("visibility_timeout", 30)
    
    def get_message_retention(self) -> int:
        """Get the message retention period in seconds."""
        return self.config.get("message_retention", 3600)
    
    def is_persistence_enabled(self) -> bool:
        """Check if message persistence is enabled."""
        return self.config.get("persistence", False)
    
    def get_dlq_name(self, base_name: str) -> str:
        """
        Get the dead letter queue name for a given queue.
        
        Args:
            base_name: Base queue name
            
        Returns:
            Dead letter queue name with prefix
        """
        dlq_name = f"{base_name}-dlq"
        return self.get_queue_name(dlq_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            "environment": self.environment,
            "backend": self.get_backend(),
            "region": self.get_region(),
            "debug": self.is_debug_enabled(),
            "persistence": self.is_persistence_enabled(),
            "retry_attempts": self.get_retry_attempts(),
            "visibility_timeout": self.get_visibility_timeout(),
            "message_retention": self.get_message_retention(),
            "queue_names": self.get_all_queue_names()
        }


# Global configuration instance
_config_instance: Optional[QueueConfig] = None


def get_queue_config(environment: Optional[str] = None) -> QueueConfig:
    """
    Get the global queue configuration instance.
    
    Args:
        environment: Environment name (optional, uses env var if not provided)
        
    Returns:
        QueueConfig instance
    """
    global _config_instance
    
    if _config_instance is None or (environment and environment != _config_instance.environment):
        _config_instance = QueueConfig(environment)
    
    return _config_instance


def reset_config():
    """Reset the global configuration instance (useful for testing)."""
    global _config_instance
    _config_instance = None


# Convenience functions
def get_queue_name(base_name: str, environment: Optional[str] = None) -> str:
    """Get queue name with environment prefix."""
    config = get_queue_config(environment)
    return config.get_queue_name(base_name)


def get_backend(environment: Optional[str] = None) -> str:
    """Get queue backend type."""
    config = get_queue_config(environment)
    return config.get_backend()


def is_local_environment(environment: Optional[str] = None) -> bool:
    """Check if running in local environment."""
    config = get_queue_config(environment)
    return config.get_backend() == "local"


def is_sqs_environment(environment: Optional[str] = None) -> bool:
    """Check if running with SQS backend."""
    config = get_queue_config(environment)
    return config.get_backend() == "sqs"
