"""Scoring engine domain service for vehicle matching."""

from typing import List, Dict, Any, Tuple
import structlog
import math

from ..value_objects.vehicle_attributes import VehicleAttributes
from ..value_objects.match_criteria import MatchCriteria
from ..value_objects.confidence_score import ConfidenceScore
from ..entities.cvegs_entry import CVEGSEntry

logger = structlog.get_logger()


class ScoringEngine:
    """Domain service for scoring and ranking vehicle match candidates."""
    
    def __init__(self, match_criteria: MatchCriteria):
        self.criteria = match_criteria
    
    def score_candidates(self, 
                        attributes: VehicleAttributes,
                        candidates: List[CVEGSEntry]) -> List[Tuple[CVEGSEntry, float, Dict[str, float]]]:
        """
        Score all candidates and return sorted list with detailed scoring.
        
        Args:
            attributes: Extracted vehicle attributes
            candidates: List of candidate CVEGS entries
            
        Returns:
            List of tuples (candidate, total_score, score_breakdown)
        """
        if not candidates:
            return []
        
        scored_candidates = []
        
        for candidate in candidates:
            score, breakdown = self._score_single_candidate(attributes, candidate)
            scored_candidates.append((candidate, score, breakdown))
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug("Candidates scored",
                    total_candidates=len(candidates),
                    top_score=scored_candidates[0][1] if scored_candidates else 0.0)
        
        return scored_candidates
    
    def _score_single_candidate(self, 
                               attributes: VehicleAttributes,
                               candidate: CVEGSEntry) -> Tuple[float, Dict[str, float]]:
        """Score a single candidate against vehicle attributes."""
        
        # Initialize score breakdown
        breakdown = {
            'brand_score': 0.0,
            'model_score': 0.0,
            'year_score': 0.0,
            'attribute_score': 0.0,
            'total_score': 0.0
        }
        
        # 1. Brand matching (40% weight)
        brand_score = self._score_brand_match(attributes.brand, candidate.brand)
        breakdown['brand_score'] = brand_score
        
        # 2. Model matching (35% weight)
        model_score = self._score_model_match(attributes.model, candidate.model)
        breakdown['model_score'] = model_score
        
        # 3. Year matching (15% weight)
        year_score = self._score_year_match(attributes.year, candidate.actual_year)
        breakdown['year_score'] = year_score
        
        # 4. Enhanced attributes matching (10% weight)
        attribute_score = self._score_attributes_match(attributes, candidate)
        breakdown['attribute_score'] = attribute_score
        
        # Calculate weighted total
        total_score = (
            brand_score * self.criteria.brand_weight +
            model_score * self.criteria.model_weight +
            year_score * self.criteria.year_weight +
            attribute_score * self.criteria.attribute_weight
        )
        
        breakdown['total_score'] = total_score
        
        return total_score, breakdown
    
    def _score_brand_match(self, target_brand: str, candidate_brand: str) -> float:
        """Score brand matching with exact/fuzzy logic."""
        if not target_brand or not candidate_brand:
            return 0.0
        
        # Normalize for comparison
        target_norm = target_brand.upper().strip()
        candidate_norm = candidate_brand.upper().strip()
        
        # Exact match
        if target_norm == candidate_norm:
            return 1.0
        
        # Substring match
        if target_norm in candidate_norm or candidate_norm in target_norm:
            return 0.9
        
        # Token-based similarity
        target_tokens = set(target_norm.split())
        candidate_tokens = set(candidate_norm.split())
        
        if target_tokens and candidate_tokens:
            overlap = len(target_tokens.intersection(candidate_tokens))
            union = len(target_tokens.union(candidate_tokens))
            jaccard_score = overlap / union if union > 0 else 0.0
            
            # Scale Jaccard to be more generous for brands
            return min(0.8, jaccard_score * 1.2)
        
        return 0.0
    
    def _score_model_match(self, target_model: str, candidate_model: str) -> float:
        """Score model matching with enhanced fuzzy logic."""
        if not target_model or not candidate_model:
            return 0.0
        
        # Use the candidate's built-in similarity method
        return candidate_model.model_similarity(target_model) if hasattr(candidate_model, 'model_similarity') else 0.0
    
    def _score_year_match(self, target_year: int, candidate_year: int) -> float:
        """Score year matching with tolerance."""
        if not target_year or not candidate_year:
            return 0.0
        
        year_diff = abs(target_year - candidate_year)
        
        if year_diff == 0:
            return 1.0
        elif year_diff == 1:
            return 0.9
        elif year_diff == 2:
            return 0.7
        elif year_diff <= 5:
            return 0.5
        else:
            return 0.1
    
    def _score_attributes_match(self, 
                               attributes: VehicleAttributes,
                               candidate: CVEGSEntry) -> float:
        """Score enhanced attributes matching."""
        if not attributes.has_enhanced_attributes:
            return 0.5  # Neutral score when no enhanced attributes
        
        attribute_scores = []
        weights = []
        
        # Fuel type matching
        if attributes.fuel_type and self._candidate_has_fuel_info(candidate):
            fuel_score = self._score_fuel_type_match(attributes, candidate)
            attribute_scores.append(fuel_score)
            weights.append(self.criteria.fuel_type_weight)
        
        # Drivetrain matching
        if attributes.drivetrain and self._candidate_has_drivetrain_info(candidate):
            drivetrain_score = self._score_drivetrain_match(attributes, candidate)
            attribute_scores.append(drivetrain_score)
            weights.append(self.criteria.drivetrain_weight)
        
        # Body style matching
        if attributes.body_style and self._candidate_has_body_info(candidate):
            body_score = self._score_body_style_match(attributes, candidate)
            attribute_scores.append(body_score)
            weights.append(self.criteria.body_style_weight)
        
        # Trim level matching
        if attributes.trim_level and self._candidate_has_trim_info(candidate):
            trim_score = self._score_trim_level_match(attributes, candidate)
            attribute_scores.append(trim_score)
            weights.append(self.criteria.trim_level_weight)
        
        if not attribute_scores:
            return 0.3  # Low score when no attributes can be matched
        
        # Calculate weighted average
        total_weight = sum(weights)
        if total_weight > 0:
            weighted_score = sum(score * weight for score, weight in zip(attribute_scores, weights)) / total_weight
            return weighted_score
        
        return 0.3
    
    def _score_fuel_type_match(self, attributes: VehicleAttributes, candidate: CVEGSEntry) -> float:
        """Score fuel type matching."""
        # Extract fuel type from candidate description
        candidate_fuel = self._extract_fuel_from_description(candidate.description)
        
        if not candidate_fuel:
            return 0.0
        
        # Use normalized comparison
        if attributes.matches_fuel_type(candidate_fuel):
            return 1.0
        
        return 0.0
    
    def _score_drivetrain_match(self, attributes: VehicleAttributes, candidate: CVEGSEntry) -> float:
        """Score drivetrain matching."""
        candidate_drivetrain = self._extract_drivetrain_from_description(candidate.description)
        
        if not candidate_drivetrain:
            return 0.0
        
        if attributes.matches_drivetrain(candidate_drivetrain):
            return 1.0
        
        return 0.0
    
    def _score_body_style_match(self, attributes: VehicleAttributes, candidate: CVEGSEntry) -> float:
        """Score body style matching."""
        candidate_body = self._extract_body_style_from_description(candidate.description)
        
        if not candidate_body:
            return 0.0
        
        if attributes.matches_body_style(candidate_body):
            return 1.0
        
        return 0.0
    
    def _score_trim_level_match(self, attributes: VehicleAttributes, candidate: CVEGSEntry) -> float:
        """Score trim level matching."""
        if not attributes.trim_level:
            return 0.0
        
        # Simple keyword matching for trim levels
        if attributes.trim_level.upper() in candidate.description.upper():
            return 1.0
        
        return 0.0
    
    def _candidate_has_fuel_info(self, candidate: CVEGSEntry) -> bool:
        """Check if candidate has fuel type information."""
        fuel_keywords = ['DIESEL', 'TD', 'TDI', 'GASOLINA', 'GASOLINE', 'GAS', 'NAFTA', 
                        'ELECTRIC', 'ELECTRICO', 'HYBRID', 'HIBRIDO']
        return any(keyword in candidate.description.upper() for keyword in fuel_keywords)
    
    def _candidate_has_drivetrain_info(self, candidate: CVEGSEntry) -> bool:
        """Check if candidate has drivetrain information."""
        drivetrain_keywords = ['4X4', '4WD', 'AWD', '4X2', '2WD', 'FWD', 'RWD']
        return any(keyword in candidate.description.upper() for keyword in drivetrain_keywords)
    
    def _candidate_has_body_info(self, candidate: CVEGSEntry) -> bool:
        """Check if candidate has body style information."""
        body_keywords = ['DC', 'SC', 'SEDAN', 'SUV', 'HATCHBACK', 'PICKUP', 'CAMIONETA', 
                        'DOBLE CABINA', 'CABINA SIMPLE', 'SPORT UTILITY']
        return any(keyword in candidate.description.upper() for keyword in body_keywords)
    
    def _candidate_has_trim_info(self, candidate: CVEGSEntry) -> bool:
        """Check if candidate has trim level information."""
        trim_keywords = ['DENALI', 'PREMIUM', 'LUXURY', 'SPORT', 'LX', 'EX', 'DX', 
                        'LIMITED', 'ULTIMATE', 'TITANIUM', 'PLATINUM']
        return any(keyword in candidate.description.upper() for keyword in trim_keywords)
    
    def _extract_fuel_from_description(self, description: str) -> str:
        """Extract fuel type from description."""
        desc_upper = description.upper()
        
        fuel_mappings = {
            'DIESEL': 'DIESEL',
            'TD': 'DIESEL',
            'TDI': 'DIESEL',
            'GASOLINA': 'GASOLINE',
            'GASOLINE': 'GASOLINE',
            'GAS': 'GASOLINE',
            'NAFTA': 'GASOLINE',
            'ELECTRIC': 'ELECTRIC',
            'ELECTRICO': 'ELECTRIC',
            'HYBRID': 'HYBRID',
            'HIBRIDO': 'HYBRID'
        }
        
        for keyword, fuel_type in fuel_mappings.items():
            if keyword in desc_upper:
                return fuel_type
        
        return None
    
    def _extract_drivetrain_from_description(self, description: str) -> str:
        """Extract drivetrain from description."""
        desc_upper = description.upper()
        
        drivetrain_mappings = {
            '4X4': '4X4',
            '4WD': '4X4',
            'AWD': 'AWD',
            '4X2': '4X2',
            '2WD': '4X2',
            'FWD': 'FWD',
            'RWD': 'RWD'
        }
        
        for keyword, drivetrain in drivetrain_mappings.items():
            if keyword in desc_upper:
                return drivetrain
        
        return None
    
    def _extract_body_style_from_description(self, description: str) -> str:
        """Extract body style from description."""
        desc_upper = description.upper()
        
        body_mappings = {
            'DC': 'DOUBLE_CAB',
            'DOBLE CABINA': 'DOUBLE_CAB',
            'DOUBLE CAB': 'DOUBLE_CAB',
            'SC': 'SINGLE_CAB',
            'CABINA SIMPLE': 'SINGLE_CAB',
            'SINGLE CAB': 'SINGLE_CAB',
            'SEDAN': 'SEDAN',
            '4P': 'SEDAN',
            'SUV': 'SUV',
            'SPORT UTILITY': 'SUV',
            'HATCHBACK': 'HATCHBACK',
            '5P': 'HATCHBACK',
            'PICKUP': 'PICKUP',
            'CAMIONETA': 'PICKUP'
        }
        
        for keyword, body_style in body_mappings.items():
            if keyword in desc_upper:
                return body_style
        
        return None
    
    def calculate_confidence(self, 
                           best_score: float,
                           score_breakdown: Dict[str, float],
                           attributes: VehicleAttributes) -> ConfidenceScore:
        """
        Calculate final confidence score with multiple factors.
        
        Factors:
        - Base matching score
        - Data completeness
        - Excel vs LLM confidence
        - Score distribution analysis
        """
        # Base confidence from matching score
        base_confidence = best_score
        
        # Boost confidence for high Excel confidence
        excel_boost = 0.0
        if attributes.excel_confidence > 0.8:
            excel_boost = 0.1 * attributes.excel_confidence
        
        # Boost confidence for complete attributes
        completeness_boost = 0.05 * attributes.completeness_score
        
        # Boost confidence for strong individual component scores
        component_boost = 0.0
        if score_breakdown.get('brand_score', 0) >= 0.9:
            component_boost += 0.05
        if score_breakdown.get('model_score', 0) >= 0.9:
            component_boost += 0.05
        if score_breakdown.get('year_score', 0) >= 0.9:
            component_boost += 0.03
        
        # Calculate final confidence
        final_confidence = min(1.0, base_confidence + excel_boost + completeness_boost + component_boost)
        
        return ConfidenceScore(final_confidence)