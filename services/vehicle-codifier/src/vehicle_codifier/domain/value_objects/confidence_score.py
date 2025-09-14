"""Confidence score value object."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ConfidenceScore:
    """Immutable value object representing a confidence score."""
    
    score: float
    
    def __post_init__(self):
        """Validate confidence score."""
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0: {self.score}")
    
    @property
    def level(self) -> Literal["high", "medium", "low", "very_low"]:
        """Get confidence level based on score."""
        if self.score >= 0.85:
            return "high"
        elif self.score >= 0.65:
            return "medium"
        elif self.score >= 0.45:
            return "low"
        else:
            return "very_low"
    
    @property
    def is_acceptable(self) -> bool:
        """Check if confidence is acceptable for matching."""
        return self.score >= 0.45
    
    @property
    def percentage(self) -> float:
        """Get confidence as percentage."""
        return self.score * 100
    
    def __str__(self) -> str:
        """Human readable representation."""
        return f"ConfidenceScore({self.score:.3f}, {self.level})"