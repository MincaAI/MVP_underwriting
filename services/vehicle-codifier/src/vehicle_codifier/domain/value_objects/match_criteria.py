"""Match criteria value object for vehicle matching."""

from dataclasses import dataclass
from typing import Optional, Set, Dict, Any


@dataclass(frozen=True)
class MatchCriteria:
    """Immutable value object representing matching criteria and weights."""
    
    # Core matching weights
    brand_weight: float = 0.40
    model_weight: float = 0.35
    year_weight: float = 0.15
    attribute_weight: float = 0.10
    
    # Attribute-specific weights
    fuel_type_weight: float = 0.30
    drivetrain_weight: float = 0.25
    body_style_weight: float = 0.25
    trim_level_weight: float = 0.20
    
    # Matching thresholds
    min_confidence_threshold: float = 0.45
    exact_match_threshold: float = 0.95
    fuzzy_match_threshold: float = 0.80
    
    # Search parameters
    max_candidates: int = 100
    fuzzy_similarity_cutoff: float = 0.60
    token_overlap_threshold: float = 0.30
    
    # Required attributes for high confidence
    required_attributes: Optional[Set[str]] = None
    
    def __post_init__(self):
        """Validate criteria invariants."""
        # Validate weights sum approximately to 1.0 for core matching
        core_sum = self.brand_weight + self.model_weight + self.year_weight + self.attribute_weight
        if not (0.95 <= core_sum <= 1.05):
            raise ValueError(f"Core matching weights must sum to ~1.0: {core_sum}")
        
        # Validate attribute weights sum approximately to 1.0
        attr_sum = (self.fuel_type_weight + self.drivetrain_weight + 
                   self.body_style_weight + self.trim_level_weight)
        if not (0.95 <= attr_sum <= 1.05):
            raise ValueError(f"Attribute weights must sum to ~1.0: {attr_sum}")
        
        # Validate thresholds are in valid range
        for threshold in [self.min_confidence_threshold, self.exact_match_threshold, 
                         self.fuzzy_match_threshold, self.fuzzy_similarity_cutoff,
                         self.token_overlap_threshold]:
            if not (0.0 <= threshold <= 1.0):
                raise ValueError(f"Thresholds must be between 0.0 and 1.0: {threshold}")
        
        # Validate logical threshold ordering
        if not (self.min_confidence_threshold <= self.fuzzy_match_threshold <= self.exact_match_threshold):
            raise ValueError("Thresholds must be in logical order: min <= fuzzy <= exact")
        
        # Validate search parameters
        if self.max_candidates <= 0:
            raise ValueError("Max candidates must be positive")
        
        # Set default required attributes if None
        if self.required_attributes is None:
            object.__setattr__(self, 'required_attributes', {"brand", "model"})
    
    @property
    def core_weights(self) -> Dict[str, float]:
        """Get core matching weights as dictionary."""
        return {
            "brand": self.brand_weight,
            "model": self.model_weight,
            "year": self.year_weight,
            "attributes": self.attribute_weight
        }
    
    @property
    def attribute_weights(self) -> Dict[str, float]:
        """Get attribute-specific weights as dictionary."""
        return {
            "fuel_type": self.fuel_type_weight,
            "drivetrain": self.drivetrain_weight,
            "body_style": self.body_style_weight,
            "trim_level": self.trim_level_weight
        }
    
    @property
    def thresholds(self) -> Dict[str, float]:
        """Get all thresholds as dictionary."""
        return {
            "min_confidence": self.min_confidence_threshold,
            "exact_match": self.exact_match_threshold,
            "fuzzy_match": self.fuzzy_match_threshold,
            "fuzzy_similarity_cutoff": self.fuzzy_similarity_cutoff,
            "token_overlap": self.token_overlap_threshold
        }
    
    def is_high_confidence_match(self, score: float) -> bool:
        """Check if score qualifies as high confidence."""
        return score >= self.exact_match_threshold
    
    def is_acceptable_match(self, score: float) -> bool:
        """Check if score meets minimum threshold."""
        return score >= self.min_confidence_threshold
    
    def requires_attribute(self, attribute: str) -> bool:
        """Check if an attribute is required for matching."""
        return attribute in self.required_attributes
    
    @classmethod
    def create_strict(cls) -> 'MatchCriteria':
        """Create strict matching criteria."""
        return cls(
            min_confidence_threshold=0.70,
            exact_match_threshold=0.95,
            fuzzy_match_threshold=0.85,
            fuzzy_similarity_cutoff=0.75,
            required_attributes={"brand", "model", "year"}
        )
    
    @classmethod
    def create_lenient(cls) -> 'MatchCriteria':
        """Create lenient matching criteria."""
        return cls(
            min_confidence_threshold=0.35,
            exact_match_threshold=0.85,
            fuzzy_match_threshold=0.70,
            fuzzy_similarity_cutoff=0.50,
            required_attributes={"brand"}
        )
    
    def with_weights(self, **weight_updates) -> 'MatchCriteria':
        """Create new criteria with updated weights."""
        current_dict = {
            'brand_weight': self.brand_weight,
            'model_weight': self.model_weight,
            'year_weight': self.year_weight,
            'attribute_weight': self.attribute_weight,
            'fuel_type_weight': self.fuel_type_weight,
            'drivetrain_weight': self.drivetrain_weight,
            'body_style_weight': self.body_style_weight,
            'trim_level_weight': self.trim_level_weight,
            'min_confidence_threshold': self.min_confidence_threshold,
            'exact_match_threshold': self.exact_match_threshold,
            'fuzzy_match_threshold': self.fuzzy_match_threshold,
            'max_candidates': self.max_candidates,
            'fuzzy_similarity_cutoff': self.fuzzy_similarity_cutoff,
            'token_overlap_threshold': self.token_overlap_threshold,
            'required_attributes': self.required_attributes
        }
        current_dict.update(weight_updates)
        return MatchCriteria(**current_dict)
    
    def __str__(self) -> str:
        """Human readable representation."""
        return f"MatchCriteria(min_conf={self.min_confidence_threshold}, weights=B{self.brand_weight}/M{self.model_weight}/Y{self.year_weight})"