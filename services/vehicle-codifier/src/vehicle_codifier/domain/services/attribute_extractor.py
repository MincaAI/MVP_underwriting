"""Attribute extraction domain service."""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import structlog

from ..value_objects.vehicle_attributes import VehicleAttributes
from ..entities.vehicle import Vehicle

logger = structlog.get_logger()


class IAttributeExtractor(ABC):
    """Interface for attribute extraction services."""
    
    @abstractmethod
    async def extract_attributes(self, 
                               vehicle: Vehicle, 
                               context: Optional[Dict[str, Any]] = None) -> VehicleAttributes:
        """Extract vehicle attributes from description and context."""
        pass


class AttributeExtractor:
    """Domain service for extracting and combining vehicle attributes."""
    
    def __init__(self, 
                 preprocessor: IAttributeExtractor,
                 llm_extractor: IAttributeExtractor):
        self.preprocessor = preprocessor
        self.llm_extractor = llm_extractor
    
    async def extract_comprehensive_attributes(self, vehicle: Vehicle) -> VehicleAttributes:
        """
        Extract comprehensive vehicle attributes using multiple sources.
        
        Priority hierarchy:
        1. Excel pre-extracted data (highest confidence)
        2. LLM extraction from description (medium confidence)
        3. Rule-based preprocessing (lowest confidence)
        
        Args:
            vehicle: Vehicle entity with description and Excel data
            
        Returns:
            VehicleAttributes with combined data from all sources
        """
        logger.debug("Extracting comprehensive attributes", 
                    vehicle_id=vehicle.insurer_id)
        
        # Step 1: Start with Excel attributes (highest confidence)
        excel_attributes = vehicle.to_attributes()
        
        # Step 2: Extract using rule-based preprocessing
        context = {
            'known_brand': vehicle.brand,
            'known_model': vehicle.model,
            'known_year': vehicle.year
        }
        
        rule_based_attributes = await self.preprocessor.extract_attributes(
            vehicle, context
        )
        
        # Step 3: Extract using LLM (for detailed attributes)
        llm_attributes = await self.llm_extractor.extract_attributes(
            vehicle, context
        )
        
        # Step 4: Combine attributes with priority hierarchy
        combined_attributes = self._combine_attributes(
            excel_attributes,
            rule_based_attributes, 
            llm_attributes
        )
        
        logger.debug("Attributes extracted successfully",
                    excel_confidence=combined_attributes.excel_confidence,
                    llm_confidence=combined_attributes.llm_confidence,
                    completeness=combined_attributes.completeness_score)
        
        return combined_attributes
    
    def _combine_attributes(self, 
                          excel_attributes: VehicleAttributes,
                          rule_based_attributes: VehicleAttributes,
                          llm_attributes: VehicleAttributes) -> VehicleAttributes:
        """
        Combine attributes from multiple sources with priority hierarchy.
        
        Excel data takes precedence over LLM data, which takes precedence over rule-based data.
        """
        # Start with rule-based attributes (lowest priority)
        result = rule_based_attributes
        
        # Override with LLM attributes (medium priority)
        result = result.merge_with(llm_attributes)
        
        # Override with Excel attributes (highest priority)
        result = result.merge_with(excel_attributes)
        
        # Ensure confidence scores reflect the sources used
        final_excel_confidence = excel_attributes.excel_confidence
        final_llm_confidence = max(llm_attributes.llm_confidence, rule_based_attributes.llm_confidence)
        
        # Create final result with proper confidence scores
        return VehicleAttributes(
            brand=result.brand,
            model=result.model,
            year=result.year,
            vin=result.vin,
            coverage_package=result.coverage_package,
            fuel_type=result.fuel_type,
            drivetrain=result.drivetrain,
            body_style=result.body_style,
            trim_level=result.trim_level,
            engine_size=result.engine_size,
            transmission=result.transmission,
            doors=result.doors,
            excel_confidence=final_excel_confidence,
            llm_confidence=final_llm_confidence
        )
    
    def validate_attributes(self, attributes: VehicleAttributes) -> Dict[str, bool]:
        """
        Validate extracted attributes for consistency.
        
        Returns:
            Dictionary of validation results for each attribute
        """
        validation_results = {}
        
        # Validate core attributes
        validation_results['has_core_attributes'] = attributes.has_core_attributes
        validation_results['has_excel_data'] = attributes.has_excel_data
        validation_results['has_enhanced_attributes'] = attributes.has_enhanced_attributes
        
        # Validate year consistency
        if attributes.year:
            validation_results['year_valid'] = 1900 <= attributes.year <= 2030
        else:
            validation_results['year_valid'] = True
        
        # Validate attribute normalization
        if attributes.fuel_type:
            normalized_fuel = attributes.normalize_fuel_type()
            validation_results['fuel_type_normalized'] = normalized_fuel is not None
        else:
            validation_results['fuel_type_normalized'] = True
        
        if attributes.drivetrain:
            normalized_drivetrain = attributes.normalize_drivetrain()
            validation_results['drivetrain_normalized'] = normalized_drivetrain is not None
        else:
            validation_results['drivetrain_normalized'] = True
        
        if attributes.body_style:
            normalized_body = attributes.normalize_body_style()
            validation_results['body_style_normalized'] = normalized_body is not None
        else:
            validation_results['body_style_normalized'] = True
        
        return validation_results