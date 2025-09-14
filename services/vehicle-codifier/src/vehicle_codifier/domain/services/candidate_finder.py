"""Candidate finding domain service."""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import structlog
import pandas as pd

from ..value_objects.vehicle_attributes import VehicleAttributes
from ..value_objects.match_criteria import MatchCriteria
from ..entities.cvegs_entry import CVEGSEntry

logger = structlog.get_logger()


class ICVEGSRepository(ABC):
    """Interface for CVEGS data access."""
    
    @abstractmethod
    def find_by_brand_and_year(self, 
                              insurer_id: str,
                              brand: str, 
                              year: Optional[int] = None) -> List[CVEGSEntry]:
        """Find CVEGS entries by brand and year."""
        pass
    
    @abstractmethod
    def find_by_criteria(self, 
                        insurer_id: str,
                        criteria: Dict[str, Any]) -> List[CVEGSEntry]:
        """Find CVEGS entries by multiple criteria."""
        pass
    
    @abstractmethod
    def search_text(self, 
                   insurer_id: str,
                   search_text: str,
                   limit: int = 100) -> List[CVEGSEntry]:
        """Search CVEGS entries by text similarity."""
        pass


class CandidateFinder:
    """Domain service for finding candidate vehicle matches."""
    
    def __init__(self, 
                 cvegs_repository: ICVEGSRepository,
                 match_criteria: MatchCriteria):
        self.cvegs_repository = cvegs_repository
        self.match_criteria = match_criteria
    
    def find_candidates(self, 
                       insurer_id: str,
                       attributes: VehicleAttributes) -> List[CVEGSEntry]:
        """
        Find candidate matches using progressive filtering strategy.
        
        Strategy:
        1. Exact match on brand + year (if available)
        2. Fuzzy match on model within brand
        3. Fallback to text-based search
        4. Progressive relaxation if needed
        
        Args:
            insurer_id: Insurance company identifier
            attributes: Extracted vehicle attributes
            
        Returns:
            List of candidate CVEGS entries
        """
        logger.debug("Finding candidates", 
                    insurer_id=insurer_id,
                    brand=attributes.brand,
                    year=attributes.year)
        
        # Strategy 1: Exact brand + year matching
        if attributes.brand and attributes.year:
            candidates = self._find_by_brand_and_year(
                insurer_id, attributes.brand, attributes.year
            )
            
            if candidates:
                # Filter by model within brand matches
                if attributes.model:
                    candidates = self._filter_by_model_fuzzy(candidates, attributes.model)
                
                if len(candidates) >= 5:  # Sufficient candidates found
                    return self._limit_candidates(candidates)
        
        # Strategy 2: Brand-only matching
        if attributes.brand:
            candidates = self._find_by_brand_and_year(
                insurer_id, attributes.brand, None
            )
            
            if attributes.model:
                candidates = self._filter_by_model_fuzzy(candidates, attributes.model)
            
            if len(candidates) >= 5:
                return self._limit_candidates(candidates)
        
        # Strategy 3: Text-based search fallback
        candidates = self._find_by_text_search(insurer_id, attributes)
        
        # Strategy 4: Progressive relaxation
        if len(candidates) < 5:
            relaxed_candidates = self._find_with_relaxed_criteria(insurer_id, attributes)
            candidates.extend(relaxed_candidates)
        
        return self._limit_candidates(candidates)
    
    def _find_by_brand_and_year(self, 
                               insurer_id: str,
                               brand: str, 
                               year: Optional[int]) -> List[CVEGSEntry]:
        """Find candidates by exact brand and year match."""
        try:
            candidates = self.cvegs_repository.find_by_brand_and_year(
                insurer_id, brand, year
            )
            
            logger.debug("Brand/year candidates found",
                        brand=brand,
                        year=year,
                        count=len(candidates))
            
            return candidates
            
        except Exception as e:
            logger.error("Error finding by brand/year", 
                        brand=brand, year=year, error=str(e))
            return []
    
    def _filter_by_model_fuzzy(self, 
                              candidates: List[CVEGSEntry], 
                              target_model: str) -> List[CVEGSEntry]:
        """Filter candidates by fuzzy model matching."""
        if not target_model:
            return candidates
        
        scored_candidates = []
        
        for candidate in candidates:
            similarity = candidate.model_similarity(target_model)
            if similarity >= self.match_criteria.fuzzy_similarity_cutoff:
                scored_candidates.append((candidate, similarity))
        
        # Sort by similarity score (descending)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        filtered = [candidate for candidate, _ in scored_candidates]
        
        logger.debug("Model fuzzy filtering",
                    target_model=target_model,
                    original_count=len(candidates),
                    filtered_count=len(filtered))
        
        return filtered
    
    def _find_by_text_search(self, 
                           insurer_id: str,
                           attributes: VehicleAttributes) -> List[CVEGSEntry]:
        """Find candidates using text-based search."""
        search_terms = []
        
        if attributes.brand:
            search_terms.append(attributes.brand)
        if attributes.model:
            search_terms.append(attributes.model)
        if attributes.year:
            search_terms.append(str(attributes.year))
        
        search_text = " ".join(search_terms)
        
        if not search_text:
            return []
        
        try:
            candidates = self.cvegs_repository.search_text(
                insurer_id, search_text, self.match_criteria.max_candidates
            )
            
            logger.debug("Text search candidates",
                        search_text=search_text,
                        count=len(candidates))
            
            return candidates
            
        except Exception as e:
            logger.error("Error in text search", 
                        search_text=search_text, error=str(e))
            return []
    
    def _find_with_relaxed_criteria(self, 
                                  insurer_id: str,
                                  attributes: VehicleAttributes) -> List[CVEGSEntry]:
        """Find additional candidates with relaxed criteria."""
        relaxed_candidates = []
        
        # Try year range matching (±2 years)
        if attributes.brand and attributes.year:
            for year_offset in [-2, -1, 1, 2]:
                relaxed_year = attributes.year + year_offset
                if 1900 <= relaxed_year <= 2030:
                    year_candidates = self._find_by_brand_and_year(
                        insurer_id, attributes.brand, relaxed_year
                    )
                    relaxed_candidates.extend(year_candidates)
        
        # Try partial brand matching
        if attributes.brand and len(attributes.brand) > 3:
            partial_brand = attributes.brand[:3]
            criteria = {'brand_prefix': partial_brand}
            partial_candidates = self.cvegs_repository.find_by_criteria(
                insurer_id, criteria
            )
            relaxed_candidates.extend(partial_candidates)
        
        logger.debug("Relaxed criteria candidates",
                    count=len(relaxed_candidates))
        
        return relaxed_candidates
    
    def _limit_candidates(self, candidates: List[CVEGSEntry]) -> List[CVEGSEntry]:
        """Limit candidates to maximum allowed."""
        if len(candidates) <= self.match_criteria.max_candidates:
            return candidates
        
        # Prioritize candidates with complete attributes
        prioritized = sorted(candidates, 
                           key=lambda c: (c.actual_year is not None,
                                        len(c.description),
                                        len(c.search_tokens)),
                           reverse=True)
        
        limited = prioritized[:self.match_criteria.max_candidates]
        
        logger.debug("Candidates limited",
                    original_count=len(candidates),
                    limited_count=len(limited))
        
        return limited
    
    def validate_candidates(self, candidates: List[CVEGSEntry]) -> Dict[str, Any]:
        """
        Validate candidate quality and provide diagnostics.
        
        Returns:
            Dictionary with validation metrics
        """
        if not candidates:
            return {
                'total_candidates': 0,
                'valid_candidates': 0,
                'has_year_data': 0,
                'brand_diversity': 0,
                'quality_score': 0.0
            }
        
        valid_candidates = [c for c in candidates if c.brand and c.model]
        candidates_with_year = [c for c in candidates if c.actual_year]
        unique_brands = set(c.brand for c in candidates if c.brand)
        
        # Calculate quality score
        completeness_scores = []
        for candidate in candidates:
            score = 0.0
            if candidate.brand: score += 0.3
            if candidate.model: score += 0.3
            if candidate.actual_year: score += 0.2
            if len(candidate.description) > 10: score += 0.2
            completeness_scores.append(score)
        
        avg_quality = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
        
        return {
            'total_candidates': len(candidates),
            'valid_candidates': len(valid_candidates),
            'has_year_data': len(candidates_with_year),
            'brand_diversity': len(unique_brands),
            'quality_score': avg_quality,
            'completeness_distribution': {
                'high': sum(1 for s in completeness_scores if s >= 0.8),
                'medium': sum(1 for s in completeness_scores if 0.5 <= s < 0.8),
                'low': sum(1 for s in completeness_scores if s < 0.5)
            }
        }