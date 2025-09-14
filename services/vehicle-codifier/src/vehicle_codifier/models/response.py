from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime


class APIResponse(BaseModel):
    """Base API response model."""
    
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Unique request identifier")


class SuccessResponse(APIResponse):
    """Success response model."""
    
    success: bool = Field(True, description="Success flag")
    data: Optional[Any] = Field(None, description="Response data")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Request processed successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_123456789",
                "data": {}
            }
        }


class ErrorResponse(APIResponse):
    """Error response model."""
    
    success: bool = Field(False, description="Success flag")
    error_code: str = Field(..., description="Error code")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "An error occurred while processing the request",
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_123456789",
                "error_code": "VALIDATION_ERROR",
                "error_details": {
                    "field": "description",
                    "issue": "Description cannot be empty"
                }
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """Validation error response model."""
    
    error_code: str = Field("VALIDATION_ERROR", description="Error code")
    validation_errors: Optional[list] = Field(None, description="List of validation errors")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "Validation failed",
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_123456789",
                "error_code": "VALIDATION_ERROR",
                "validation_errors": [
                    {
                        "field": "description",
                        "message": "Description cannot be empty",
                        "type": "value_error"
                    }
                ]
            }
        }
