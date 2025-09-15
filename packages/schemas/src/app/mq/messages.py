#!/usr/bin/env python3
"""
Message schema definitions for the MQ system.
Provides validation and type safety for queue messages.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class MessageType(str, Enum):
    """Supported message types."""
    PRE_ANALYSIS = "pre_analysis"
    EXTRACT = "extract"
    TRANSFORM = "transform"
    EXPORT = "export"
    MATCHING = "matching"


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class BaseMessage(BaseModel):
    """Base message schema with common fields."""
    
    # Message metadata
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique correlation ID for tracking message flow"
    )
    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique message identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message creation timestamp"
    )
    version: str = Field(
        default="1.0",
        description="Message schema version"
    )
    message_type: MessageType = Field(
        description="Type of message for routing and processing"
    )
    
    # Processing metadata
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retry attempts"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts"
    )
    
    # Optional tracing
    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed tracing ID"
    )
    parent_message_id: Optional[str] = Field(
        default=None,
        description="ID of parent message in processing chain"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('correlation_id', 'message_id', 'trace_id', 'parent_message_id')
    def validate_ids(cls, v):
        """Validate ID formats."""
        if v is not None and not isinstance(v, str):
            raise ValueError("IDs must be strings")
        return v


class PreAnalysisMessage(BaseMessage):
    """Message for pre-analysis of email attachments."""
    
    message_type: Literal[MessageType.PRE_ANALYSIS] = Field(default=MessageType.PRE_ANALYSIS)
    
    # Required fields
    case_id: str = Field(description="Case identifier")
    email_message_id: int = Field(description="Email message ID from database")
    
    # Email metadata
    from_email: str = Field(description="Email sender address")
    subject: str = Field(description="Email subject")
    content: Optional[str] = Field(default="", description="Email content")
    
    # Attachments information
    attachments: List[Dict[str, Any]] = Field(
        description="List of attachment information",
        default_factory=list
    )
    
    # Processing configuration
    profile: Optional[str] = Field(
        default="generic.yaml",
        description="Processing profile to use"
    )
    
    @validator('attachments')
    def validate_attachments(cls, v):
        """Validate attachments list."""
        if not v or len(v) == 0:
            raise ValueError("At least one attachment is required for pre-analysis")
        
        # Validate each attachment has required fields
        required_fields = ['s3_uri', 'original_name', 'file_size']
        for i, attachment in enumerate(v):
            for field in required_fields:
                if field not in attachment:
                    raise ValueError(f"Attachment {i+1} missing required field: {field}")
            
            # Validate S3 URI format
            if not attachment['s3_uri'].startswith('s3://'):
                raise ValueError(f"Attachment {i+1} s3_uri must start with 's3://'")
        
        return v


class ExtractMessage(BaseMessage):
    """Message for document extraction requests."""
    
    message_type: Literal[MessageType.EXTRACT] = Field(default=MessageType.EXTRACT)
    
    # Required fields
    run_id: str = Field(description="Unique run identifier")
    s3_uri: str = Field(description="S3 URI of file to extract")
    
    # Optional fields
    case_id: Optional[str] = Field(
        default=None,
        description="Associated case ID"
    )
    file_type: Optional[str] = Field(
        default=None,
        description="Type of file (xlsx, csv, pdf, etc.)"
    )
    extraction_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Extraction configuration parameters"
    )
    
    @validator('s3_uri')
    def validate_s3_uri(cls, v):
        """Validate S3 URI format."""
        if not v.startswith('s3://'):
            raise ValueError("s3_uri must start with 's3://'")
        return v


class TransformMessage(BaseMessage):
    """Message for data transformation requests."""
    
    message_type: Literal[MessageType.TRANSFORM] = Field(default=MessageType.TRANSFORM)
    
    # Required fields
    run_id: str = Field(description="Unique run identifier")
    extracted_data_uri: str = Field(description="S3 URI of extracted data")
    
    # Optional fields
    case_id: Optional[str] = Field(
        default=None,
        description="Associated case ID"
    )
    transformation_rules: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Transformation rules and configuration"
    )
    output_format: Optional[str] = Field(
        default="json",
        description="Desired output format"
    )
    
    @validator('extracted_data_uri')
    def validate_data_uri(cls, v):
        """Validate data URI format."""
        if not v.startswith('s3://'):
            raise ValueError("extracted_data_uri must start with 's3://'")
        return v


class ExportMessage(BaseMessage):
    """Message for data export requests."""
    
    message_type: Literal[MessageType.EXPORT] = Field(default=MessageType.EXPORT)
    
    # Required fields
    run_id: str = Field(description="Unique run identifier")
    transformed_data_uri: str = Field(description="S3 URI of transformed data")
    
    # Optional fields
    case_id: Optional[str] = Field(
        default=None,
        description="Associated case ID"
    )
    export_format: Optional[str] = Field(
        default="xlsx",
        description="Export format (xlsx, csv, json)"
    )
    export_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Export configuration parameters"
    )
    destination_uri: Optional[str] = Field(
        default=None,
        description="Specific destination URI for export"
    )
    
    @validator('transformed_data_uri')
    def validate_data_uri(cls, v):
        """Validate data URI format."""
        if not v.startswith('s3://'):
            raise ValueError("transformed_data_uri must start with 's3://'")
        return v


class VehicleMatchingMessage(BaseMessage):
    """Message for vehicle matching requests."""
    
    message_type: Literal[MessageType.MATCHING] = Field(default=MessageType.MATCHING)
    
    # Required fields
    run_id: str = Field(description="Unique run identifier")
    vehicle_descriptions: List[str] = Field(
        description="List of vehicle descriptions to match"
    )
    
    # Optional fields
    case_id: Optional[str] = Field(
        default=None,
        description="Associated case ID"
    )
    insurer_id: Optional[str] = Field(
        default="default",
        description="Insurer identifier for matching rules"
    )
    matching_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Matching configuration parameters"
    )
    confidence_threshold: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for matches"
    )
    
    @validator('vehicle_descriptions')
    def validate_descriptions(cls, v):
        """Validate vehicle descriptions."""
        if not v or len(v) == 0:
            raise ValueError("vehicle_descriptions cannot be empty")
        return v


class ErrorMessage(BaseMessage):
    """Message for error reporting and handling."""
    
    message_type: MessageType = Field(default="error", description="Message type for error messages")
    
    # Required fields
    error_type: str = Field(description="Type of error")
    error_message: str = Field(description="Error description")
    failed_message: Dict[str, Any] = Field(description="Original failed message")
    
    # Optional fields
    error_code: Optional[str] = Field(
        default=None,
        description="Specific error code"
    )
    stack_trace: Optional[str] = Field(
        default=None,
        description="Error stack trace"
    )
    recovery_suggestions: Optional[List[str]] = Field(
        default_factory=list,
        description="Suggested recovery actions"
    )


class StatusUpdateMessage(BaseMessage):
    """Message for status updates."""
    
    message_type: MessageType = Field(default="status", description="Message type for status updates")
    
    # Required fields
    run_id: str = Field(description="Run identifier")
    status: MessageStatus = Field(description="Current status")
    
    # Optional fields
    progress_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)"
    )
    status_message: Optional[str] = Field(
        default=None,
        description="Human-readable status message"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional status metadata"
    )


# Message type mapping for validation
MESSAGE_TYPE_MAP = {
    MessageType.PRE_ANALYSIS: PreAnalysisMessage,
    MessageType.EXTRACT: ExtractMessage,
    MessageType.TRANSFORM: TransformMessage,
    MessageType.EXPORT: ExportMessage,
    MessageType.MATCHING: VehicleMatchingMessage,
}


def validate_message(message_data: Dict[str, Any]) -> BaseMessage:
    """
    Validate and parse a message based on its type.
    
    Args:
        message_data: Raw message data
        
    Returns:
        Validated message instance
        
    Raises:
        ValueError: If message is invalid
        KeyError: If message type is unknown
    """
    message_type = message_data.get('message_type')
    if not message_type:
        raise ValueError("Message must include 'message_type' field")
    
    if message_type not in MESSAGE_TYPE_MAP:
        raise KeyError(f"Unknown message type: {message_type}")
    
    message_class = MESSAGE_TYPE_MAP[message_type]
    return message_class(**message_data)


def create_pre_analysis_message(
    case_id: str,
    email_message_id: int,
    from_email: str,
    subject: str,
    attachments: List[Dict[str, Any]],
    content: str = "",
    **kwargs
) -> PreAnalysisMessage:
    """Create a validated pre-analysis message."""
    return PreAnalysisMessage(
        case_id=case_id,
        email_message_id=email_message_id,
        from_email=from_email,
        subject=subject,
        content=content,
        attachments=attachments,
        **kwargs
    )


def create_extract_message(
    run_id: str,
    s3_uri: str,
    case_id: Optional[str] = None,
    **kwargs
) -> ExtractMessage:
    """Create a validated extract message."""
    return ExtractMessage(
        run_id=run_id,
        s3_uri=s3_uri,
        case_id=case_id,
        **kwargs
    )


def create_transform_message(
    run_id: str,
    extracted_data_uri: str,
    case_id: Optional[str] = None,
    **kwargs
) -> TransformMessage:
    """Create a validated transform message."""
    return TransformMessage(
        run_id=run_id,
        extracted_data_uri=extracted_data_uri,
        case_id=case_id,
        **kwargs
    )


def create_export_message(
    run_id: str,
    transformed_data_uri: str,
    case_id: Optional[str] = None,
    **kwargs
) -> ExportMessage:
    """Create a validated export message."""
    return ExportMessage(
        run_id=run_id,
        transformed_data_uri=transformed_data_uri,
        case_id=case_id,
        **kwargs
    )


def create_matching_message(
    run_id: str,
    vehicle_descriptions: List[str],
    case_id: Optional[str] = None,
    **kwargs
) -> VehicleMatchingMessage:
    """Create a validated vehicle matching message."""
    return VehicleMatchingMessage(
        run_id=run_id,
        vehicle_descriptions=vehicle_descriptions,
        case_id=case_id,
        **kwargs
    )


def message_to_dict(message: BaseMessage) -> Dict[str, Any]:
    """
    Convert a message to dictionary format for queue transmission.
    
    Args:
        message: Message instance
        
    Returns:
        Dictionary representation
    """
    return message.dict(exclude_none=True)


def dict_to_message(data: Dict[str, Any]) -> BaseMessage:
    """
    Convert dictionary data back to message instance.
    
    Args:
        data: Dictionary data
        
    Returns:
        Message instance
    """
    return validate_message(data)
