"""Match result domain entity."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..value_objects.confidence_score import ConfidenceScore
from ..value_objects.vehicle_attributes import VehicleAttributes
from .cvegs_entry import CVEGSEntry


@dataclass(frozen=True)
class MatchResult:
    """Represents the result of a vehicle matching operation."""
    
    # Core match information
    cvegs_code: str
    confidence: ConfidenceScore
    matched_entry: CVEGSEntry
    
    # Extracted attributes
    extracted_attributes: VehicleAttributes
    
    # Processing metadata
    processing_time_ms: float
    candidates_evaluated: int
    match_method: str
    
    # Enhanced matching details
    attribute_matches: Optional[Dict[str, bool]] = None
    tie_breaker_used: bool = False
    source_row: Optional[int] = None
    
    # Diagnostics and warnings
    warnings: List[str] = None
    
    def __post_init__(self):
        """Validate entity invariants."""
        if not self.cvegs_code:
            raise ValueError("CVEGS code cannot be empty")
        
        if self.processing_time_ms < 0:
            raise ValueError("Processing time cannot be negative")
        
        if self.candidates_evaluated < 0:
            raise ValueError("Candidates evaluated cannot be negative")
        
        if not self.match_method:
            raise ValueError("Match method cannot be empty")
        
        # Set default warnings if None
        if self.warnings is None:
            object.__setattr__(self, 'warnings', [])
    
    @property
    def is_successful_match(self) -> bool:
        """Check if this is a successful match (not error or no match)."""
        return self.cvegs_code not in ["NO_MATCH", "ERROR", "BATCH_ERROR"]
    
    @property
    def confidence_level(self) -> str:
        """Get string representation of confidence level."""
        return self.confidence.level
    
    @property
    def confidence_score(self) -> float:
        """Get numeric confidence score."""
        return self.confidence.score
    
    @property
    def matched_brand(self) -> str:
        """Get matched brand from the CVEGS entry."""
        return self.matched_entry.brand
    
    @property
    def matched_model(self) -> str:
        """Get matched model from the CVEGS entry."""
        return self.matched_entry.model
    
    @property
    def matched_year(self) -> Optional[int]:
        """Get matched year from the CVEGS entry."""
        return self.matched_entry.actual_year
    
    @property
    def matched_description(self) -> str:
        """Get matched description from the CVEGS entry."""
        return self.matched_entry.description
    
    def has_attribute_match(self, attribute: str) -> Optional[bool]:
        """Check if a specific attribute was matched."""
        if not self.attribute_matches:
            return None
        return self.attribute_matches.get(attribute)
    
    def add_warning(self, warning: str) -> 'MatchResult':
        """Add a warning to the result (returns new instance)."""
        new_warnings = list(self.warnings) + [warning]
        return self._replace(warnings=new_warnings)
    
    def _replace(self, **kwargs) -> 'MatchResult':
        """Create a new instance with replaced fields."""
        current_dict = {
            'cvegs_code': self.cvegs_code,
            'confidence': self.confidence,
            'matched_entry': self.matched_entry,
            'extracted_attributes': self.extracted_attributes,
            'processing_time_ms': self.processing_time_ms,
            'candidates_evaluated': self.candidates_evaluated,
            'match_method': self.match_method,
            'attribute_matches': self.attribute_matches,
            'tie_breaker_used': self.tie_breaker_used,
            'source_row': self.source_row,
            'warnings': self.warnings
        }
        current_dict.update(kwargs)
        return MatchResult(**current_dict)
    
    @classmethod
    def create_successful_match(cls,
                               cvegs_entry: CVEGSEntry,
                               confidence_score: float,
                               extracted_attributes: VehicleAttributes,
                               processing_time_ms: float,
                               candidates_evaluated: int,
                               match_method: str,
                               attribute_matches: Optional[Dict[str, bool]] = None,
                               tie_breaker_used: bool = False,
                               source_row: Optional[int] = None) -> 'MatchResult':
        """Create a successful match result."""
        confidence = ConfidenceScore(confidence_score)
        
        return cls(
            cvegs_code=cvegs_entry.cvegs_code,
            confidence=confidence,
            matched_entry=cvegs_entry,
            extracted_attributes=extracted_attributes,
            processing_time_ms=processing_time_ms,
            candidates_evaluated=candidates_evaluated,
            match_method=match_method,
            attribute_matches=attribute_matches,
            tie_breaker_used=tie_breaker_used,
            source_row=source_row,
            warnings=[]
        )
    
    @classmethod
    def create_no_match(cls,
                       extracted_attributes: VehicleAttributes,
                       processing_time_ms: float,
                       candidates_evaluated: int,
                       source_row: Optional[int] = None) -> 'MatchResult':
        """Create a no match result."""
        # Create a placeholder CVEGS entry for no match
        no_match_entry = CVEGSEntry(
            cvegs_code="NO_MATCH",
            brand="",
            model="",
            description="No match found"
        )
        
        confidence = ConfidenceScore(0.0)
        
        return cls(
            cvegs_code="NO_MATCH",
            confidence=confidence,
            matched_entry=no_match_entry,
            extracted_attributes=extracted_attributes,
            processing_time_ms=processing_time_ms,
            candidates_evaluated=candidates_evaluated,
            match_method="no_match",
            source_row=source_row,
            warnings=["No matching vehicle found in dataset"]
        )
    
    @classmethod
    def create_error(cls,
                    error_message: str,
                    extracted_attributes: Optional[VehicleAttributes] = None,
                    processing_time_ms: float = 0.0,
                    source_row: Optional[int] = None) -> 'MatchResult':
        """Create an error result."""
        # Create a placeholder CVEGS entry for error
        error_entry = CVEGSEntry(
            cvegs_code="ERROR",
            brand="",
            model="",
            description="Error occurred during matching"
        )
        
        if extracted_attributes is None:
            extracted_attributes = VehicleAttributes()
        
        confidence = ConfidenceScore(0.0)
        
        return cls(
            cvegs_code="ERROR",
            confidence=confidence,
            matched_entry=error_entry,
            extracted_attributes=extracted_attributes,
            processing_time_ms=processing_time_ms,
            candidates_evaluated=0,
            match_method="error",
            source_row=source_row,
            warnings=[f"Error: {error_message}"]
        )
    
    def __str__(self) -> str:
        """Human readable representation."""
        return f"MatchResult({self.cvegs_code}, confidence={self.confidence_score:.3f}, {self.match_method})"