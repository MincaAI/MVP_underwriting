import json
import asyncio
from typing import Optional, Dict, Any
import openai
from openai import AsyncOpenAI
import structlog

from ..config.settings import get_settings
from ..models.vehicle import VehicleAttributes

logger = structlog.get_logger()


class LLMAttributeExtractor:
    """Uses OpenAI LLM to extract vehicle attributes from descriptions."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        
        # System prompt for attribute extraction
        self.system_prompt = """You are an expert vehicle analyst specializing in extracting structured information from vehicle descriptions.

Your task is to extract vehicle attributes from free-form descriptions and return them in a structured JSON format.

IMPORTANT RULES:
1. Return ONLY valid JSON - no additional text or explanations
2. Use null for missing information - never guess or hallucinate
3. Normalize values to standard formats
4. Be consistent with naming conventions

For Spanish terms, use these mappings:
- "DIESEL" = diesel
- "GASOLINA" = gasoline  
- "4X4" = 4x4
- "4X2" = 4x2
- "DC" (Doble Cabina) = double_cab
- "SC" (Simple Cabina) = single_cab
- "PUERTAS" = doors (extract number)

Brand normalization:
- "GM" = "GENERAL MOTORS"
- Keep other brands as provided but in proper case

Return JSON with these exact fields:
{
  "brand": "string or null",
  "model": "string or null", 
  "year": "integer or null",
  "fuel_type": "string or null",
  "drivetrain": "string or null",
  "body_style": "string or null",
  "engine_size": "string or null",
  "transmission": "string or null",
  "trim_level": "string or null",
  "doors": "integer or null"
}"""

        # User prompt template
        self.user_prompt_template = """Extract vehicle attributes from this description:

"{description}"

Return the structured JSON with the vehicle attributes."""
        
        # Enhanced prompt template with Excel context
        self.enhanced_prompt_template = """Extract vehicle attributes from this description, considering known information from Excel:

Description: "{description}"

Known from Excel (high confidence):
- Brand: {known_brand}
- Model: {known_model}
- Year: {known_year}

Focus on extracting ADDITIONAL attributes from the description:
- fuel_type (DIESEL, GASOLINA, etc.)
- drivetrain (4X4, 4X2, etc.)
- body_style (DOUBLE_CAB, SEDAN, etc.)
- trim_level (DENALI, PREMIUM, etc.)
- transmission (MANUAL, AUTOMATICO)
- engine_size

Return JSON with ALL attributes (including the known ones):"""

    async def extract_attributes(self, 
                               description: str,
                               known_brand: Optional[str] = None,
                               known_model: Optional[str] = None, 
                               known_year: Optional[int] = None) -> VehicleAttributes:
        """
        Extract vehicle attributes using OpenAI LLM with Excel context.
        
        Args:
            description: Vehicle description to analyze
            known_brand: Brand from Excel (high confidence)
            known_model: Model from Excel (high confidence) 
            known_year: Year from Excel (high confidence)
            
        Returns:
            VehicleAttributes object with extracted information
        """
        if not description or not description.strip():
            return VehicleAttributes()
        
        try:
            # Prepare the prompt (enhanced if we have Excel context)
            if known_brand or known_model or known_year:
                user_prompt = self.enhanced_prompt_template.format(
                    description=description.strip(),
                    known_brand=known_brand or "Unknown",
                    known_model=known_model or "Unknown", 
                    known_year=known_year or "Unknown"
                )
            else:
                user_prompt = self.user_prompt_template.format(description=description.strip())
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.settings.openai_max_tokens,
                temperature=self.settings.openai_temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            if not content:
                logger.warning("Empty response from OpenAI", description=description)
                return VehicleAttributes()
            
            # Parse JSON response
            try:
                attributes_dict = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON from OpenAI", 
                           content=content, error=str(e))
                return VehicleAttributes()
            
            # Create VehicleAttributes object, ensuring Excel data takes precedence
            if known_brand:
                attributes_dict['brand'] = known_brand
            if known_model:
                attributes_dict['model'] = known_model
            if known_year:
                attributes_dict['year'] = known_year
            
            # Set LLM confidence based on context
            attributes_dict['llm_confidence'] = 0.9 if (known_brand and known_model) else 0.7
            
            attributes = VehicleAttributes(**attributes_dict)
            
            logger.info("Successfully extracted attributes",
                       description=description,
                       extracted_brand=attributes.brand,
                       extracted_model=attributes.model,
                       extracted_year=attributes.year)
            
            return attributes
            
        except openai.RateLimitError as e:
            logger.error("OpenAI rate limit exceeded", error=str(e))
            raise
        except openai.APIError as e:
            logger.error("OpenAI API error", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in LLM extraction", 
                        description=description, error=str(e))
            return VehicleAttributes()
    
    async def extract_attributes_batch(self, descriptions: list[str]) -> list[VehicleAttributes]:
        """
        Extract attributes for multiple descriptions in parallel.
        
        Args:
            descriptions: List of vehicle descriptions
            
        Returns:
            List of VehicleAttributes objects
        """
        if not descriptions:
            return []
        
        # Create tasks for parallel processing
        tasks = [self.extract_attributes(desc) for desc in descriptions]
        
        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_requests)
        
        async def bounded_extract(description: str) -> VehicleAttributes:
            async with semaphore:
                return await self.extract_attributes(description)
        
        # Run all extractions in parallel with bounded concurrency
        bounded_tasks = [bounded_extract(desc) for desc in descriptions]
        results = await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        # Handle any exceptions and return valid results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Failed to extract attributes for description",
                           index=i, description=descriptions[i], error=str(result))
                final_results.append(VehicleAttributes())
            else:
                final_results.append(result)
        
        return final_results
    
    async def enhance_attributes(self, 
                               basic_attributes: VehicleAttributes, 
                               description: str) -> VehicleAttributes:
        """
        Enhance basic attributes with additional LLM analysis.
        
        Args:
            basic_attributes: Attributes extracted by rule-based preprocessing
            description: Original description
            
        Returns:
            Enhanced VehicleAttributes object
        """
        enhancement_prompt = f"""Given this vehicle description and the basic attributes already extracted, 
provide additional details that might be missing:

Description: "{description}"

Already extracted:
- Brand: {basic_attributes.brand}
- Model: {basic_attributes.model}
- Year: {basic_attributes.year}
- Fuel Type: {basic_attributes.fuel_type}
- Drivetrain: {basic_attributes.drivetrain}
- Body Style: {basic_attributes.body_style}

Please provide any missing attributes or corrections in JSON format:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enhancement_prompt}
                ],
                max_tokens=self.settings.openai_max_tokens,
                temperature=self.settings.openai_temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                enhanced_dict = json.loads(content)
                
                # Merge with basic attributes, preferring non-null enhanced values
                merged_dict = basic_attributes.dict()
                for key, value in enhanced_dict.items():
                    if value is not None and key in merged_dict:
                        merged_dict[key] = value
                
                return VehicleAttributes(**merged_dict)
                
        except Exception as e:
            logger.warning("Failed to enhance attributes", error=str(e))
        
        # Return original attributes if enhancement fails
        return basic_attributes
    
    async def validate_extraction(self, 
                                attributes: VehicleAttributes, 
                                description: str) -> Dict[str, Any]:
        """
        Validate extracted attributes against the original description.
        
        Args:
            attributes: Extracted attributes
            description: Original description
            
        Returns:
            Validation results with confidence score and warnings
        """
        validation_prompt = f"""Validate if these extracted attributes match the vehicle description:

Description: "{description}"

Extracted Attributes:
- Brand: {attributes.brand}
- Model: {attributes.model}
- Year: {attributes.year}
- Fuel Type: {attributes.fuel_type}
- Drivetrain: {attributes.drivetrain}
- Body Style: {attributes.body_style}

Return JSON with:
{{
  "confidence_score": 0.0-1.0,
  "is_valid": true/false,
  "warnings": ["list of any issues found"],
  "missing_info": ["list of info that seems missing"]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a validation expert. Return only JSON."},
                    {"role": "user", "content": validation_prompt}
                ],
                max_tokens=500,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
                
        except Exception as e:
            logger.warning("Failed to validate extraction", error=str(e))
        
        # Default validation result
        return {
            "confidence_score": 0.5,
            "is_valid": True,
            "warnings": [],
            "missing_info": []
        }
    
    async def call_openai(self, prompt: str, max_tokens: int = 150) -> str:
        """Direct call to OpenAI for simple text responses (like tie-breaker)."""
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return content.strip() if content else ""
            
        except Exception as e:
            logger.error("Direct OpenAI call failed", error=str(e))
            return ""
