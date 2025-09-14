"""Clean architecture controllers for vehicle matching."""

import time
from typing import List, Dict, Any
from datetime import datetime
import structlog

from fastapi import HTTPException

from ...domain.entities.vehicle import Vehicle
from ...domain.entities.match_result import MatchResult as DomainMatchResult
from ...application.use_cases.match_single_vehicle import MatchSingleVehicleUseCase
from ...application.use_cases.match_vehicle_batch import MatchVehicleBatchUseCase
from ...infrastructure.di_container import get_container

# Legacy models for API compatibility
from ...models.vehicle import VehicleInput, MatchResult, BatchMatchRequest, BatchMatchResponse

logger = structlog.get_logger()


class VehicleMatchingController:
    """Clean architecture controller for vehicle matching operations."""
    
    def __init__(self):
        self.container = get_container()
    
    async def match_single_vehicle(self, vehicle_input: VehicleInput) -> MatchResult:
        """
        Match a single vehicle using clean architecture.
        
        Args:
            vehicle_input: Legacy API model input
            
        Returns:
            Legacy API model result
        """
        try:
            logger.info("Clean architecture single vehicle match request", 
                       description=vehicle_input.description[:50],
                       brand=vehicle_input.brand,
                       model=vehicle_input.model,
                       year=vehicle_input.year,
                       insurer_id=vehicle_input.insurer_id,
                       source_row=vehicle_input.source_row)
            
            # Convert API model to domain entity
            vehicle = self._convert_to_domain_vehicle(vehicle_input)
            
            # Get use case from DI container
            use_case = self.container.get('match_single_vehicle_use_case')
            
            # Execute use case
            domain_result = await use_case.execute(vehicle)
            
            # Convert domain result back to API model
            api_result = self._convert_to_api_result(domain_result)
            
            logger.info("Clean architecture single vehicle match completed",
                       cvegs_code=api_result.cvegs_code,
                       confidence_score=api_result.confidence_score,
                       match_method=api_result.match_method,
                       tie_breaker_used=getattr(api_result, 'tie_breaker_used', False))
            
            return api_result
            
        except Exception as e:
            logger.error("Clean architecture single vehicle match failed", 
                        description=vehicle_input.description[:50],
                        brand=vehicle_input.brand,
                        source_row=vehicle_input.source_row,
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")
    
    async def match_batch_vehicles(self, batch_request: BatchMatchRequest) -> BatchMatchResponse:
        """
        Match multiple vehicles using clean architecture.
        
        Args:
            batch_request: Legacy API batch request
            
        Returns:
            Legacy API batch response
        """
        try:
            # Count vehicles with Excel data for logging
            excel_data_count = sum(1 for v in batch_request.vehicles 
                                  if v.brand or v.model or v.year)
            
            logger.info("Clean architecture batch vehicle match request",
                       vehicle_count=len(batch_request.vehicles),
                       excel_data_count=excel_data_count,
                       insurer_id=batch_request.insurer_id,
                       parallel_processing=batch_request.parallel_processing)
            
            # Convert API models to domain entities
            vehicles = [self._convert_to_domain_vehicle(v) for v in batch_request.vehicles]
            
            # Get use case from DI container
            use_case = self.container.get('match_vehicle_batch_use_case')
            
            # Execute batch use case
            batch_result = await use_case.execute(vehicles, batch_request.parallel_processing)
            
            # Convert domain results to API models
            api_results = [self._convert_to_api_result(r) for r in batch_result['results']]
            
            # Create API response
            response = BatchMatchResponse(
                results=api_results,
                summary=batch_result['summary'],
                total_processing_time_ms=batch_result['total_processing_time_ms']
            )
            
            logger.info("Clean architecture batch vehicle match completed",
                       vehicle_count=len(batch_request.vehicles),
                       successful_matches=batch_result['summary']['successful_matches'],
                       success_rate=batch_result['summary']['success_rate'],
                       avg_processing_time=batch_result['summary']['performance_metrics']['average_processing_time_ms'])
            
            return response
            
        except Exception as e:
            logger.error("Clean architecture batch vehicle match failed",
                        vehicle_count=len(batch_request.vehicles),
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Batch matching failed: {str(e)}")
    
    def _convert_to_domain_vehicle(self, vehicle_input: VehicleInput) -> Vehicle:
        """Convert API model to domain entity."""
        return Vehicle.from_input(
            description=vehicle_input.description,
            insurer_id=vehicle_input.insurer_id,
            brand=vehicle_input.brand,
            model=vehicle_input.model,
            year=vehicle_input.year,
            vin=vehicle_input.vin,
            coverage_package=vehicle_input.coverage_package,
            source_row=vehicle_input.source_row
        )
    
    def _convert_to_api_result(self, domain_result: DomainMatchResult) -> MatchResult:
        """Convert domain result to API model."""
        return MatchResult(
            cvegs_code=domain_result.cvegs_code,
            confidence_score=domain_result.confidence_score,
            confidence_level=domain_result.confidence_level,
            matched_brand=domain_result.matched_brand,
            matched_model=domain_result.matched_model,
            matched_year=domain_result.matched_year,
            matched_description=domain_result.matched_description,
            extracted_attributes=domain_result.extracted_attributes,
            processing_time_ms=domain_result.processing_time_ms,
            candidates_evaluated=domain_result.candidates_evaluated,
            match_method=domain_result.match_method,
            attribute_matches=domain_result.attribute_matches,
            tie_breaker_used=domain_result.tie_breaker_used,
            source_row=domain_result.source_row,
            warnings=domain_result.warnings
        )
    
    def validate_single_vehicle_request(self, vehicle_input: VehicleInput) -> List[str]:
        """Validate single vehicle request."""
        errors = []
        
        # Required fields
        if not vehicle_input.description or not vehicle_input.description.strip():
            errors.append("Vehicle description is required")
        
        if not vehicle_input.insurer_id or not vehicle_input.insurer_id.strip():
            errors.append("Insurer ID is required")
        
        # Description length check
        if len(vehicle_input.description) > 1000:
            errors.append("Vehicle description too long (max 1000 characters)")
        
        if len(vehicle_input.description) < 5:
            errors.append("Vehicle description too short (min 5 characters)")
        
        # Year validation
        if vehicle_input.year and (vehicle_input.year < 1900 or vehicle_input.year > 2030):
            errors.append(f"Invalid year: {vehicle_input.year}")
        
        return errors
    
    def validate_batch_request(self, batch_request: BatchMatchRequest) -> List[str]:
        """Validate batch request."""
        errors = []
        
        # Check batch size limits
        if len(batch_request.vehicles) == 0:
            errors.append("Batch cannot be empty")
        
        if len(batch_request.vehicles) > 200:  # API limit
            errors.append(f"Batch size {len(batch_request.vehicles)} exceeds maximum (200)")
        
        # Check insurer ID
        if not batch_request.insurer_id or not batch_request.insurer_id.strip():
            errors.append("Insurer ID cannot be empty")
        
        # Validate individual vehicles (first 5 errors only)
        invalid_count = 0
        for i, vehicle in enumerate(batch_request.vehicles):
            vehicle_errors = self.validate_single_vehicle_request(vehicle)
            if vehicle_errors:
                invalid_count += 1
                if invalid_count <= 5:
                    errors.append(f"Vehicle {i}: {'; '.join(vehicle_errors)}")
        
        if invalid_count > 5:
            errors.append(f"Additional {invalid_count - 5} vehicles have validation errors")
        
        return errors
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status using clean architecture services."""
        try:
            container = self.container
            
            # Get health check from DI container
            health_status = container.health_check()
            
            # Get repository statistics
            cvegs_repo = container.get('cvegs_repository')
            repo_stats = cvegs_repo.get_statistics('default')
            
            return {
                'status': health_status['container_status'],
                'services': health_status['services'],
                'dataset_loaded': repo_stats.get('total_entries', 0) > 0,
                'dataset_records': repo_stats.get('total_entries', 0),
                'clean_architecture_enabled': True,
                'timestamp': datetime.utcnow(),
                'errors': health_status.get('errors', [])
            }
            
        except Exception as e:
            logger.error("Health status check failed", error=str(e))
            return {
                'status': 'unhealthy',
                'error': str(e),
                'clean_architecture_enabled': False,
                'timestamp': datetime.utcnow()
            }
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics."""
        try:
            container = self.container
            
            # Get service information
            service_info = container.get_service_info()
            
            # Get repository statistics
            cvegs_repo = container.get('cvegs_repository')
            repo_stats = cvegs_repo.get_statistics('default')
            
            return {
                'clean_architecture': {
                    'enabled': True,
                    'services': service_info,
                    'container_status': 'healthy'
                },
                'dataset_metrics': repo_stats,
                'matching_features': {
                    'excel_input_support': True,
                    'enhanced_attribute_matching': True,
                    'llm_tie_breaker': True,
                    'chunked_parallel_processing': True,
                    'confidence_scoring': True,
                    'domain_driven_design': True
                },
                'performance_optimizations': {
                    'dependency_injection': True,
                    'repository_caching': True,
                    'singleton_services': True,
                    'transient_use_cases': True
                }
            }
            
        except Exception as e:
            logger.error("Failed to get service metrics", error=str(e))
            return {
                'clean_architecture': {
                    'enabled': False,
                    'error': str(e)
                }
            }