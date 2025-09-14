"""Use case for matching a single vehicle."""

import time
import structlog
from typing import Optional

from ...domain.entities.vehicle import Vehicle
from ...domain.entities.match_result import MatchResult
from ...domain.services.attribute_extractor import AttributeExtractor
from ...domain.services.candidate_finder import CandidateFinder
from ...domain.services.scoring_engine import ScoringEngine
from ...domain.services.tie_breaker import TieBreaker
from ...domain.value_objects.match_criteria import MatchCriteria

logger = structlog.get_logger()


class MatchSingleVehicleUseCase:
    """Use case for matching a single vehicle to CVEGS database."""
    
    def __init__(self,
                 attribute_extractor: AttributeExtractor,
                 candidate_finder: CandidateFinder,
                 scoring_engine: ScoringEngine,
                 tie_breaker: TieBreaker,
                 match_criteria: Optional[MatchCriteria] = None):
        
        self.attribute_extractor = attribute_extractor
        self.candidate_finder = candidate_finder
        self.scoring_engine = scoring_engine
        self.tie_breaker = tie_breaker
        self.match_criteria = match_criteria or MatchCriteria()
    
    async def execute(self, vehicle: Vehicle) -> MatchResult:
        """
        Execute the vehicle matching use case.
        
        Process:
        1. Extract comprehensive attributes
        2. Find candidate matches
        3. Score all candidates
        4. Resolve ties if needed
        5. Calculate final confidence
        6. Create result
        
        Args:
            vehicle: Vehicle entity to match
            
        Returns:
            MatchResult with best match and metadata
        """
        start_time = time.time()
        
        logger.info("Starting vehicle matching",
                   vehicle_id=vehicle.insurer_id,
                   has_excel_data=vehicle.has_excel_data)
        
        try:
            # Step 1: Extract comprehensive attributes
            attributes = await self.attribute_extractor.extract_comprehensive_attributes(vehicle)
            
            logger.debug("Attributes extracted",
                        brand=attributes.brand,
                        model=attributes.model,
                        year=attributes.year,
                        completeness=attributes.completeness_score,
                        excel_confidence=attributes.excel_confidence,
                        llm_confidence=attributes.llm_confidence)
            
            # Step 2: Find candidates
            candidates = self.candidate_finder.find_candidates(
                vehicle.insurer_id, attributes
            )
            
            if not candidates:
                return self._create_no_match_result(vehicle, attributes, start_time)
            
            logger.debug("Candidates found", count=len(candidates))
            
            # Step 3: Score candidates
            scored_candidates = self.scoring_engine.score_candidates(attributes, candidates)
            
            if not scored_candidates:
                return self._create_no_match_result(vehicle, attributes, start_time)
            
            # Step 4: Resolve ties if needed
            best_candidate, tie_breaker_used = await self.tie_breaker.resolve_ties(
                vehicle, attributes, scored_candidates
            )
            
            # Get score breakdown for the selected candidate
            best_score = 0.0
            best_breakdown = {}
            
            for candidate, score, breakdown in scored_candidates:
                if candidate == best_candidate:
                    best_score = score
                    best_breakdown = breakdown
                    break
            
            # Step 5: Calculate final confidence
            confidence = self.scoring_engine.calculate_confidence(
                best_score, best_breakdown, attributes
            )
            
            # Step 6: Create successful match result
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Generate attribute match breakdown
            attribute_matches = self._generate_attribute_matches(attributes, best_candidate)
            
            # Generate warnings
            warnings = self._generate_warnings(attributes, best_candidate, confidence.score)
            
            result = MatchResult.create_successful_match(
                cvegs_entry=best_candidate,
                confidence_score=confidence.score,
                extracted_attributes=attributes,
                processing_time_ms=processing_time_ms,
                candidates_evaluated=len(candidates),
                match_method="clean_architecture_enhanced",
                attribute_matches=attribute_matches,
                tie_breaker_used=tie_breaker_used,
                source_row=vehicle.source_row
            )
            
            # Add warnings if any
            for warning in warnings:
                result = result.add_warning(warning)
            
            logger.info("Vehicle matched successfully",
                       cvegs_code=result.cvegs_code,
                       confidence_score=confidence.score,
                       confidence_level=confidence.level,
                       processing_time_ms=processing_time_ms,
                       tie_breaker_used=tie_breaker_used)
            
            return result
            
        except Exception as e:
            logger.error("Error during vehicle matching",
                        vehicle_id=vehicle.insurer_id,
                        error=str(e))
            
            processing_time_ms = (time.time() - start_time) * 1000
            return MatchResult.create_error(
                error_message=str(e),
                extracted_attributes=vehicle.to_attributes(),
                processing_time_ms=processing_time_ms,
                source_row=vehicle.source_row
            )
    
    def _create_no_match_result(self, 
                               vehicle: Vehicle, 
                               attributes, 
                               start_time: float) -> MatchResult:
        """Create a no match result."""
        processing_time_ms = (time.time() - start_time) * 1000
        
        return MatchResult.create_no_match(
            extracted_attributes=attributes,
            processing_time_ms=processing_time_ms,
            candidates_evaluated=0,
            source_row=vehicle.source_row
        )
    
    def _generate_attribute_matches(self, attributes, candidate) -> dict:
        """Generate attribute match breakdown."""
        matches = {}
        
        # Brand match
        if attributes.brand and candidate.brand:
            matches['brand'] = candidate.matches_brand(attributes.brand)
        
        # Model match  
        if attributes.model:
            matches['model'] = candidate.model_similarity(attributes.model) > 0.8
        
        # Year match
        if attributes.year:
            matches['year'] = candidate.matches_year(attributes.year)
        
        # Enhanced attribute matches
        if attributes.fuel_type:
            matches['fuel_type'] = 'FUEL_TYPE_KEYWORD' in candidate.description.upper()
        
        if attributes.drivetrain:
            matches['drivetrain'] = any(dt in candidate.description.upper() 
                                      for dt in ['4X4', '4WD', 'AWD', '4X2'])
        
        if attributes.body_style:
            matches['body_style'] = any(bs in candidate.description.upper() 
                                      for bs in ['SEDAN', 'SUV', 'PICKUP', 'HATCHBACK'])
        
        return matches
    
    def _generate_warnings(self, attributes, candidate, confidence_score) -> list:
        """Generate warnings for the match result."""
        warnings = []
        
        # Low confidence warning
        if confidence_score < 0.6:
            warnings.append("Low confidence match - manual review recommended")
        
        # Missing core attributes warning
        if not attributes.has_core_attributes:
            warnings.append("Incomplete vehicle attributes - brand, model, or year missing")
        
        # Excel vs LLM conflict warning
        if attributes.excel_confidence > 0.8 and attributes.llm_confidence > 0.8:
            # Check for potential conflicts
            if attributes.brand and hasattr(attributes, 'llm_brand'):
                if attributes.brand != getattr(attributes, 'llm_brand', None):
                    warnings.append("Potential conflict between Excel and LLM extracted brand")
        
        # Year mismatch warning
        if attributes.year and candidate.actual_year:
            year_diff = abs(attributes.year - candidate.actual_year)
            if year_diff > 2:
                warnings.append(f"Year mismatch: input {attributes.year} vs matched {candidate.actual_year}")
        
        # Incomplete candidate data warning
        if not candidate.actual_year:
            warnings.append("Matched entry has incomplete year data")
        
        return warnings
    
    def validate_input(self, vehicle: Vehicle) -> list:
        """
        Validate input vehicle for matching.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Required fields
        if not vehicle.description or not vehicle.description.strip():
            errors.append("Vehicle description is required")
        
        if not vehicle.insurer_id or not vehicle.insurer_id.strip():
            errors.append("Insurer ID is required")
        
        # Description length check
        if len(vehicle.description) > 1000:
            errors.append("Vehicle description too long (max 1000 characters)")
        
        if len(vehicle.description) < 5:
            errors.append("Vehicle description too short (min 5 characters)")
        
        # Year validation
        if vehicle.year and (vehicle.year < 1900 or vehicle.year > 2030):
            errors.append(f"Invalid year: {vehicle.year}")
        
        # VIN validation (basic format check)
        if vehicle.vin:
            if len(vehicle.vin) not in [11, 17]:  # Common VIN lengths
                errors.append("VIN format appears invalid")
        
        return errors