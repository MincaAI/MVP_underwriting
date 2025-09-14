"""CVEGS dataset entry domain entity."""

from dataclasses import dataclass
from typing import Optional, Set


@dataclass(frozen=True)
class CVEGSEntry:
    """Represents a single entry from the CVEGS dataset."""
    
    # Core CVEGS data
    cvegs_code: str
    brand: str
    model: str
    description: str
    
    # Additional metadata
    year_code: Optional[str] = None
    actual_year: Optional[int] = None
    
    # Search optimization fields
    search_text: Optional[str] = None
    tokens: Optional[Set[str]] = None
    brand_year: Optional[str] = None
    
    def __post_init__(self):
        """Validate entity invariants."""
        if not self.cvegs_code:
            raise ValueError("CVEGS code cannot be empty")
        
        if not self.brand:
            raise ValueError("Brand cannot be empty")
        
        if not self.model:
            raise ValueError("Model cannot be empty")
        
        if not self.description:
            raise ValueError("Description cannot be empty")
    
    @property
    def normalized_brand(self) -> str:
        """Get normalized brand name."""
        return self.brand.upper().strip()
    
    @property
    def normalized_model(self) -> str:
        """Get normalized model name."""
        return self.model.upper().strip()
    
    @property
    def full_description(self) -> str:
        """Get full searchable description."""
        if self.search_text:
            return self.search_text
        
        parts = [self.brand, self.model, self.description]
        if self.actual_year:
            parts.append(str(self.actual_year))
        
        return " ".join(parts).upper()
    
    @property
    def search_tokens(self) -> Set[str]:
        """Get search tokens for matching."""
        if self.tokens:
            return self.tokens
        
        # Generate tokens from description
        text = self.full_description
        tokens = set()
        
        # Split by whitespace and filter
        words = text.split()
        for word in words:
            if len(word) > 1 and word.isalnum():
                tokens.add(word)
        
        return tokens
    
    def matches_brand(self, target_brand: str) -> bool:
        """Check if this entry matches the target brand."""
        if not target_brand:
            return False
        
        return self.normalized_brand == target_brand.upper().strip()
    
    def matches_year(self, target_year: int) -> bool:
        """Check if this entry matches the target year."""
        if not target_year or not self.actual_year:
            return False
        
        return self.actual_year == target_year
    
    def model_similarity(self, target_model: str) -> float:
        """Calculate model similarity score (0.0 to 1.0)."""
        if not target_model:
            return 0.0
        
        target_normalized = target_model.upper().strip()
        entry_normalized = self.normalized_model
        
        # Exact match
        if entry_normalized == target_normalized:
            return 1.0
        
        # Substring match
        if target_normalized in entry_normalized or entry_normalized in target_normalized:
            return 0.9
        
        # Token overlap
        target_tokens = set(target_normalized.split())
        entry_tokens = set(entry_normalized.split())
        
        if target_tokens and entry_tokens:
            overlap = len(target_tokens.intersection(entry_tokens))
            union = len(target_tokens.union(entry_tokens))
            return overlap / union if union > 0 else 0.0
        
        return 0.0
    
    def contains_keyword(self, keyword: str) -> bool:
        """Check if entry contains a specific keyword."""
        if not keyword:
            return False
        
        return keyword.upper() in self.full_description
    
    @classmethod
    def from_dataset_row(cls,
                        cvegs_code: str,
                        brand: str,
                        model: str,
                        description: str,
                        year_code: Optional[str] = None,
                        actual_year: Optional[int] = None,
                        **kwargs) -> 'CVEGSEntry':
        """Create CVEGSEntry from dataset row."""
        
        # Generate search optimization fields
        search_text = f"{brand} {model} {description}".upper()
        
        tokens = set()
        words = search_text.split()
        for word in words:
            if len(word) > 1 and word.isalnum():
                tokens.add(word)
        
        brand_year = f"{brand.upper()}_{actual_year}" if actual_year else None
        
        return cls(
            cvegs_code=str(cvegs_code),
            brand=brand.upper().strip(),
            model=model.upper().strip(),
            description=description.upper().strip(),
            year_code=year_code,
            actual_year=actual_year,
            search_text=search_text,
            tokens=tokens,
            brand_year=brand_year
        )
    
    def __str__(self) -> str:
        """Human readable representation."""
        return f"CVEGSEntry({self.cvegs_code}: {self.brand} {self.model} {self.actual_year})"