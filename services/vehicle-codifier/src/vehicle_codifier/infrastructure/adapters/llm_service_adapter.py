"""LLM service adapters for attribute extraction and tie breaking."""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import structlog

from ...domain.services.attribute_extractor import IAttributeExtractor  
from ...domain.services.tie_breaker import ILLMService
from ...domain.entities.vehicle import Vehicle
from ...domain.entities.cvegs_entry import CVEGSEntry
from ...domain.value_objects.vehicle_attributes import VehicleAttributes
from ...services.llm_extractor import LLMAttributeExtractor as LegacyLLMExtractor
from ...services.preprocessor import VehiclePreprocessor as LegacyPreprocessor

logger = structlog.get_logger()


class LLMAttributeExtractorAdapter(IAttributeExtractor):
    """Adapter for LLM-based attribute extraction."""
    
    def __init__(self):
        self._legacy_extractor = LegacyLLMExtractor()
    
    async def extract_attributes(self, 
                               vehicle: Vehicle, 
                               context: Optional[Dict[str, Any]] = None) -> VehicleAttributes:
        """Extract attributes using LLM service."""
        
        try:
            # Prepare context for legacy extractor
            known_brand = context.get('known_brand') if context else vehicle.brand
            known_model = context.get('known_model') if context else vehicle.model  
            known_year = context.get('known_year') if context else vehicle.year
            
            # Call legacy LLM extractor
            legacy_attributes = await self._legacy_extractor.extract_attributes(
                vehicle.description,
                known_brand=known_brand,
                known_model=known_model,
                known_year=known_year
            )
            
            logger.debug("LLM attributes extracted",
                        vehicle_id=vehicle.insurer_id,
                        llm_confidence=getattr(legacy_attributes, 'llm_confidence', 0.8))
            
            return legacy_attributes
            
        except Exception as e:
            logger.error("LLM attribute extraction failed",
                        vehicle_id=vehicle.insurer_id,
                        error=str(e))
            
            # Return basic attributes on failure
            return VehicleAttributes(
                brand=vehicle.brand,
                model=vehicle.model,
                year=vehicle.year,
                vin=vehicle.vin,
                coverage_package=vehicle.coverage_package,
                llm_confidence=0.0
            )


class PreprocessorAttributeExtractorAdapter(IAttributeExtractor):
    """Adapter for rule-based preprocessing attribute extraction."""
    
    def __init__(self):
        self._legacy_preprocessor = LegacyPreprocessor()
    
    async def extract_attributes(self, 
                               vehicle: Vehicle, 
                               context: Optional[Dict[str, Any]] = None) -> VehicleAttributes:
        """Extract attributes using rule-based preprocessing."""
        
        try:
            # Prepare parameters for legacy preprocessor
            known_brand = context.get('known_brand') if context else vehicle.brand
            known_model = context.get('known_model') if context else vehicle.model
            known_year = context.get('known_year') if context else vehicle.year
            
            # Call legacy preprocessor  
            preprocessed = self._legacy_preprocessor.preprocess(
                vehicle.description,
                year=known_year,
                known_brand=known_brand,
                known_model=known_model
            )
            
            # Extract attributes from preprocessed result
            rule_attributes = preprocessed.get('attributes')
            
            if rule_attributes:
                logger.debug("Rule-based attributes extracted",
                            vehicle_id=vehicle.insurer_id)
                return rule_attributes
            else:
                # Return empty attributes if extraction failed
                return VehicleAttributes(llm_confidence=0.1)
                
        except Exception as e:
            logger.error("Rule-based attribute extraction failed",
                        vehicle_id=vehicle.insurer_id,
                        error=str(e))
            
            # Return basic attributes on failure
            return VehicleAttributes(
                brand=vehicle.brand,
                model=vehicle.model,  
                year=vehicle.year,
                llm_confidence=0.1
            )


class LLMTieBreakerService(ILLMService):
    """LLM-based tie breaker service for resolving close matches."""
    
    def __init__(self):
        self._legacy_extractor = LegacyLLMExtractor()
    
    async def resolve_tie(self, 
                         vehicle: Vehicle,
                         tied_candidates: List[CVEGSEntry]) -> Optional[CVEGSEntry]:
        """Use LLM to resolve ties between candidates."""
        
        if len(tied_candidates) < 2:
            return tied_candidates[0] if tied_candidates else None
        
        try:
            logger.info("Resolving tie using LLM",
                       vehicle_id=vehicle.insurer_id,
                       candidates_count=len(tied_candidates))
            
            # Prepare candidate descriptions for LLM
            candidate_descriptions = []
            for i, candidate in enumerate(tied_candidates):
                desc = f"Option {i+1}: {candidate.brand} {candidate.model}"
                if candidate.actual_year:
                    desc += f" {candidate.actual_year}"
                desc += f" - {candidate.description}"
                candidate_descriptions.append(desc)
            
            # Create LLM prompt for tie breaking
            prompt = self._create_tie_breaker_prompt(
                vehicle.description, 
                candidate_descriptions
            )
            
            # Call LLM service (using legacy extractor's client)
            llm_response = await self._legacy_extractor._call_llm(prompt)
            
            # Parse LLM response to select best candidate
            selected_index = self._parse_tie_breaker_response(
                llm_response, 
                len(tied_candidates)
            )
            
            if selected_index is not None and 0 <= selected_index < len(tied_candidates):
                selected_candidate = tied_candidates[selected_index]
                
                logger.info("Tie resolved by LLM",
                           selected_candidate=f"{selected_candidate.brand} {selected_candidate.model}",
                           selected_index=selected_index)
                
                return selected_candidate
            
            logger.warning("LLM returned invalid tie breaker selection")
            return None
            
        except Exception as e:
            logger.error("LLM tie breaking failed",
                        vehicle_id=vehicle.insurer_id,
                        error=str(e))
            return None
    
    def _create_tie_breaker_prompt(self, 
                                 vehicle_description: str,
                                 candidate_descriptions: List[str]) -> str:
        """Create prompt for LLM tie breaking."""
        
        candidates_text = "\n".join(candidate_descriptions)
        
        prompt = f"""
You are helping resolve a tie between multiple vehicle matches. 

Vehicle Description to Match:
{vehicle_description}

Candidate Options:
{candidates_text}

Please analyze which candidate best matches the input vehicle description. Consider:
- Brand and model accuracy
- Year compatibility  
- Technical specifications (fuel type, drivetrain, body style)
- Overall description similarity

Respond with ONLY the number of the best option (1, 2, 3, etc.). 
Do not provide explanations or additional text.

Best match option number:"""
        
        return prompt
    
    def _parse_tie_breaker_response(self, 
                                  llm_response: str, 
                                  candidate_count: int) -> Optional[int]:
        """Parse LLM response to extract selected candidate index."""
        
        try:
            # Clean the response
            cleaned = llm_response.strip().lower()
            
            # Try to extract number
            for char in cleaned:
                if char.isdigit():
                    option_number = int(char)
                    # Convert to 0-based index
                    index = option_number - 1
                    
                    if 0 <= index < candidate_count:
                        return index
            
            # Try parsing full response for "option N" patterns
            import re
            match = re.search(r'option\s+(\d+)', cleaned)
            if match:
                option_number = int(match.group(1))
                index = option_number - 1
                
                if 0 <= index < candidate_count:
                    return index
            
            logger.warning("Could not parse LLM tie breaker response",
                         response=llm_response[:100])
            return None
            
        except Exception as e:
            logger.error("Error parsing tie breaker response",
                        response=llm_response[:100],
                        error=str(e))
            return None