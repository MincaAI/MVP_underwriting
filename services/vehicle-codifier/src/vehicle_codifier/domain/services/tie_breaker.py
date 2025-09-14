"""Tie breaker domain service for resolving close vehicle matches."""

from typing import List, Tuple, Dict, Any, Optional
from abc import ABC, abstractmethod
import structlog
import asyncio

from ..value_objects.vehicle_attributes import VehicleAttributes
from ..entities.cvegs_entry import CVEGSEntry
from ..entities.vehicle import Vehicle

logger = structlog.get_logger()


class ILLMService(ABC):
    """Interface for LLM-based tie breaking."""
    
    @abstractmethod
    async def resolve_tie(self, 
                         vehicle: Vehicle,
                         tied_candidates: List[CVEGSEntry]) -> Optional[CVEGSEntry]:
        """Use LLM to resolve ties between candidates."""
        pass


class TieBreaker:
    """Domain service for resolving ties between equally-scored candidates."""
    
    def __init__(self, 
                 llm_service: Optional[ILLMService] = None,
                 tie_threshold: float = 0.05):
        self.llm_service = llm_service
        self.tie_threshold = tie_threshold  # Score difference to consider a tie
    
    async def resolve_ties(self, 
                          vehicle: Vehicle,
                          attributes: VehicleAttributes,
                          scored_candidates: List[Tuple[CVEGSEntry, float, Dict[str, float]]]) -> Tuple[CVEGSEntry, bool]:
        """
        Resolve ties between top candidates using multiple strategies.
        
        Tie-breaking strategies (in order):
        1. Rule-based tie breaking (deterministic)
        2. LLM-based tie breaking (if available)
        3. Fallback selection
        
        Args:
            vehicle: Original vehicle entity
            attributes: Extracted vehicle attributes  
            scored_candidates: List of (candidate, score, breakdown) tuples
            
        Returns:
            Tuple of (selected_candidate, tie_breaker_used)
        """
        if not scored_candidates:
            raise ValueError("No candidates provided for tie breaking")
        
        # If only one candidate, no tie to break
        if len(scored_candidates) == 1:
            return scored_candidates[0][0], False
        
        # Check for ties among top candidates
        top_score = scored_candidates[0][1]
        tied_candidates = []
        
        for candidate, score, breakdown in scored_candidates:
            if abs(score - top_score) <= self.tie_threshold:
                tied_candidates.append((candidate, score, breakdown))
            else:
                break  # Candidates are sorted by score
        
        # If no real tie exists, return top candidate
        if len(tied_candidates) <= 1:
            return scored_candidates[0][0], False
        
        logger.info("Tie detected, applying tie-breaker logic",
                   tied_count=len(tied_candidates),
                   top_score=top_score,
                   threshold=self.tie_threshold)
        
        # Strategy 1: Rule-based tie breaking
        rule_based_winner = self._rule_based_tie_breaking(
            attributes, tied_candidates
        )
        
        if rule_based_winner:
            logger.info("Tie resolved using rule-based logic")
            return rule_based_winner, True
        
        # Strategy 2: LLM-based tie breaking (if available)
        if self.llm_service:
            try:
                llm_winner = await self._llm_based_tie_breaking(
                    vehicle, [candidate for candidate, _, _ in tied_candidates]
                )
                
                if llm_winner:
                    logger.info("Tie resolved using LLM logic")
                    return llm_winner, True
                    
            except Exception as e:
                logger.warning("LLM tie breaking failed", error=str(e))
        
        # Strategy 3: Fallback selection
        fallback_winner = self._fallback_selection(tied_candidates)
        logger.info("Tie resolved using fallback logic")
        return fallback_winner, True
    
    def _rule_based_tie_breaking(self, 
                               attributes: VehicleAttributes,
                               tied_candidates: List[Tuple[CVEGSEntry, float, Dict[str, float]]]) -> Optional[CVEGSEntry]:
        """Apply rule-based logic to break ties."""
        
        # Rule 1: Prefer exact year match
        if attributes.year:
            exact_year_matches = [
                (candidate, score, breakdown) 
                for candidate, score, breakdown in tied_candidates
                if candidate.actual_year == attributes.year
            ]
            
            if len(exact_year_matches) == 1:
                logger.debug("Tie broken by exact year match")
                return exact_year_matches[0][0]
        
        # Rule 2: Prefer candidates with complete data
        complete_candidates = []
        for candidate, score, breakdown in tied_candidates:
            completeness_score = self._calculate_candidate_completeness(candidate)
            complete_candidates.append((candidate, score, breakdown, completeness_score))
        
        # Sort by completeness (descending)
        complete_candidates.sort(key=lambda x: x[3], reverse=True)
        
        # Check if top candidate has significantly better completeness
        if len(complete_candidates) >= 2:
            top_completeness = complete_candidates[0][3]
            second_completeness = complete_candidates[1][3]
            
            if top_completeness - second_completeness >= 0.2:  # 20% better
                logger.debug("Tie broken by data completeness")
                return complete_candidates[0][0]
        
        # Rule 3: Prefer newer vehicles (if year available)
        year_candidates = [
            (candidate, score, breakdown)
            for candidate, score, breakdown in tied_candidates
            if candidate.actual_year is not None
        ]
        
        if year_candidates:
            year_candidates.sort(key=lambda x: x[0].actual_year, reverse=True)
            newest_year = year_candidates[0][0].actual_year
            
            newest_candidates = [
                (candidate, score, breakdown)
                for candidate, score, breakdown in year_candidates
                if candidate.actual_year == newest_year
            ]
            
            if len(newest_candidates) == 1:
                logger.debug("Tie broken by newest year")
                return newest_candidates[0][0]
        
        # Rule 4: Prefer candidates with stronger individual component scores
        best_component_candidate = None
        best_component_score = -1
        
        for candidate, score, breakdown in tied_candidates:
            # Calculate component strength (brand + model scores)
            brand_score = breakdown.get('brand_score', 0)
            model_score = breakdown.get('model_score', 0)
            component_strength = brand_score + model_score
            
            if component_strength > best_component_score:
                best_component_score = component_strength
                best_component_candidate = candidate
        
        if best_component_candidate and best_component_score > 1.5:  # Strong components
            logger.debug("Tie broken by component strength")
            return best_component_candidate
        
        return None  # No clear rule-based winner
    
    async def _llm_based_tie_breaking(self, 
                                    vehicle: Vehicle,
                                    tied_candidates: List[CVEGSEntry]) -> Optional[CVEGSEntry]:
        """Use LLM to intelligently resolve ties."""
        
        if not self.llm_service or len(tied_candidates) < 2:
            return None
        
        try:
            # Use LLM service to resolve the tie
            winner = await asyncio.wait_for(
                self.llm_service.resolve_tie(vehicle, tied_candidates),
                timeout=30.0  # 30 second timeout
            )
            
            # Validate that winner is actually one of the tied candidates
            if winner and winner in tied_candidates:
                return winner
            
            logger.warning("LLM returned invalid tie breaker result")
            return None
            
        except asyncio.TimeoutError:
            logger.warning("LLM tie breaking timed out")
            return None
        except Exception as e:
            logger.error("LLM tie breaking error", error=str(e))
            return None
    
    def _fallback_selection(self, 
                          tied_candidates: List[Tuple[CVEGSEntry, float, Dict[str, float]]]) -> CVEGSEntry:
        """Fallback selection when other methods fail."""
        
        # Prefer candidates with the most detailed descriptions
        detailed_candidates = []
        for candidate, score, breakdown in tied_candidates:
            detail_score = len(candidate.description) + len(candidate.search_tokens or set())
            detailed_candidates.append((candidate, detail_score))
        
        # Sort by detail score (descending)
        detailed_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Check for significantly more detailed candidate
        if len(detailed_candidates) >= 2:
            top_detail = detailed_candidates[0][1]
            second_detail = detailed_candidates[1][1]
            
            if top_detail > second_detail * 1.2:  # 20% more detailed
                logger.debug("Fallback selection by description detail")
                return detailed_candidates[0][0]
        
        # Final fallback: first candidate (stable selection)
        logger.debug("Fallback selection: first candidate")
        return tied_candidates[0][0]
    
    def _calculate_candidate_completeness(self, candidate: CVEGSEntry) -> float:
        """Calculate completeness score for a candidate."""
        completeness = 0.0
        
        # Required fields
        if candidate.cvegs_code:
            completeness += 0.2
        if candidate.brand:
            completeness += 0.2  
        if candidate.model:
            completeness += 0.2
        if candidate.description:
            completeness += 0.2
        
        # Optional but valuable fields
        if candidate.actual_year:
            completeness += 0.1
        if candidate.search_text and len(candidate.search_text) > 20:
            completeness += 0.05
        if candidate.tokens and len(candidate.tokens) > 3:
            completeness += 0.05
        
        return min(1.0, completeness)
    
    def analyze_ties(self, 
                    scored_candidates: List[Tuple[CVEGSEntry, float, Dict[str, float]]]) -> Dict[str, Any]:
        """
        Analyze the distribution of scores to identify potential ties.
        
        Returns:
            Dictionary with tie analysis results
        """
        if len(scored_candidates) < 2:
            return {
                'has_ties': False,
                'tie_count': 0,
                'score_spread': 0.0,
                'top_score': scored_candidates[0][1] if scored_candidates else 0.0
            }
        
        scores = [score for _, score, _ in scored_candidates]
        top_score = scores[0]
        
        # Count ties at different thresholds
        strict_ties = sum(1 for score in scores if abs(score - top_score) <= 0.01)
        loose_ties = sum(1 for score in scores if abs(score - top_score) <= self.tie_threshold)
        
        # Calculate score distribution
        score_spread = max(scores) - min(scores)
        score_std = sum((score - sum(scores)/len(scores))**2 for score in scores) / len(scores)
        score_std = score_std ** 0.5
        
        return {
            'has_ties': loose_ties > 1,
            'tie_count': loose_ties,
            'strict_tie_count': strict_ties,
            'score_spread': score_spread,
            'score_std': score_std,
            'top_score': top_score,
            'tie_threshold': self.tie_threshold,
            'requires_tie_breaking': loose_ties > 1
        }