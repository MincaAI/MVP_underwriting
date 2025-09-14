"""Use case for batch vehicle matching."""

import asyncio
import time
from typing import List, Dict, Any
import structlog

from ...domain.entities.vehicle import Vehicle
from ...domain.entities.match_result import MatchResult
from .match_single_vehicle import MatchSingleVehicleUseCase

logger = structlog.get_logger()


class MatchVehicleBatchUseCase:
    """Use case for batch processing of vehicle matches."""
    
    def __init__(self,
                 single_match_use_case: MatchSingleVehicleUseCase,
                 max_concurrent_requests: int = 10,
                 chunk_size: int = 50):
        
        self.single_match_use_case = single_match_use_case
        self.max_concurrent_requests = max_concurrent_requests
        self.chunk_size = chunk_size
    
    async def execute(self, 
                     vehicles: List[Vehicle],
                     parallel_processing: bool = True) -> Dict[str, Any]:
        """
        Execute batch vehicle matching.
        
        Args:
            vehicles: List of vehicles to match
            parallel_processing: Whether to process in parallel
            
        Returns:
            Dictionary with results and summary statistics
        """
        start_time = time.time()
        
        logger.info("Starting batch vehicle matching",
                   vehicle_count=len(vehicles),
                   parallel_processing=parallel_processing)
        
        # Validate batch
        validation_errors = self._validate_batch(vehicles)
        if validation_errors:
            raise ValueError(f"Batch validation failed: {'; '.join(validation_errors)}")
        
        try:
            # Process vehicles
            if parallel_processing:
                results = await self._process_parallel(vehicles)
            else:
                results = await self._process_sequential(vehicles)
            
            # Calculate total processing time
            total_time_ms = (time.time() - start_time) * 1000
            
            # Generate comprehensive summary
            summary = self._generate_comprehensive_summary(results, total_time_ms)
            
            logger.info("Batch processing completed",
                       vehicle_count=len(vehicles),
                       successful_matches=summary['successful_matches'],
                       total_time_ms=total_time_ms,
                       avg_time_per_vehicle=total_time_ms / len(vehicles))
            
            return {
                'results': results,
                'summary': summary,
                'total_processing_time_ms': total_time_ms,
                'processing_metadata': {
                    'parallel_processing': parallel_processing,
                    'chunk_size': self.chunk_size,
                    'max_concurrent': self.max_concurrent_requests
                }
            }
            
        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            # Return partial results if any were processed
            return {
                'results': [],
                'summary': self._create_error_summary(str(e)),
                'total_processing_time_ms': (time.time() - start_time) * 1000,
                'error': str(e)
            }
    
    async def _process_parallel(self, vehicles: List[Vehicle]) -> List[MatchResult]:
        """Process vehicles in parallel with chunking strategy."""
        
        # Split into chunks to avoid overwhelming the system
        chunks = [vehicles[i:i+self.chunk_size] 
                 for i in range(0, len(vehicles), self.chunk_size)]
        
        logger.info("Processing in parallel chunks",
                   total_vehicles=len(vehicles),
                   chunks=len(chunks),
                   chunk_size=self.chunk_size)
        
        all_results = []
        
        # Process chunks sequentially to control resource usage
        for chunk_idx, chunk in enumerate(chunks):
            logger.debug("Processing chunk",
                        chunk_index=chunk_idx + 1,
                        chunk_total=len(chunks),
                        vehicles_in_chunk=len(chunk))
            
            chunk_results = await self._process_chunk_parallel(chunk)
            all_results.extend(chunk_results)
            
            # Small delay between chunks to respect rate limits
            if chunk_idx < len(chunks) - 1:
                await asyncio.sleep(0.1)
        
        return all_results
    
    async def _process_chunk_parallel(self, chunk: List[Vehicle]) -> List[MatchResult]:
        """Process a chunk of vehicles in parallel with controlled concurrency."""
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def bounded_match(vehicle: Vehicle) -> MatchResult:
            """Match a single vehicle with concurrency control."""
            async with semaphore:
                try:
                    return await self.single_match_use_case.execute(vehicle)
                except Exception as e:
                    logger.error("Failed to match vehicle in batch",
                               vehicle_description=vehicle.description[:50],
                               source_row=vehicle.source_row,
                               error=str(e))
                    
                    # Return error result instead of failing the whole batch
                    return MatchResult.create_error(
                        error_message=f"Batch processing error: {str(e)}",
                        extracted_attributes=vehicle.to_attributes(),
                        processing_time_ms=0.0,
                        source_row=vehicle.source_row
                    )
        
        # Create tasks for all vehicles in chunk
        tasks = [bounded_match(vehicle) for vehicle in chunk]
        
        # Execute all tasks and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that weren't caught
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Unhandled exception in chunk processing",
                           vehicle_index=i,
                           error=str(result))
                
                # Create error result for this vehicle
                error_result = MatchResult.create_error(
                    error_message=f"Unhandled batch error: {str(result)}",
                    extracted_attributes=chunk[i].to_attributes(),
                    processing_time_ms=0.0,
                    source_row=chunk[i].source_row
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        return final_results
    
    async def _process_sequential(self, vehicles: List[Vehicle]) -> List[MatchResult]:
        """Process vehicles sequentially (for debugging or rate limiting)."""
        
        results = []
        
        for i, vehicle in enumerate(vehicles):
            try:
                logger.debug("Processing vehicle sequentially",
                           index=i + 1,
                           total=len(vehicles),
                           description=vehicle.description[:50])
                
                result = await self.single_match_use_case.execute(vehicle)
                results.append(result)
                
            except Exception as e:
                logger.error("Failed to match vehicle in sequential batch",
                           index=i,
                           description=vehicle.description[:50],
                           error=str(e))
                
                error_result = MatchResult.create_error(
                    error_message=f"Sequential processing error: {str(e)}",
                    extracted_attributes=vehicle.to_attributes(),
                    processing_time_ms=0.0,
                    source_row=vehicle.source_row
                )
                results.append(error_result)
        
        return results
    
    def _generate_comprehensive_summary(self, 
                                      results: List[MatchResult], 
                                      total_time_ms: float) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        
        if not results:
            return self._create_empty_summary()
        
        # Basic counts
        total_vehicles = len(results)
        successful_matches = sum(1 for r in results if r.is_successful_match)
        failed_matches = total_vehicles - successful_matches
        
        # Confidence distribution
        confidence_dist = {'high': 0, 'medium': 0, 'low': 0, 'very_low': 0}
        confidence_scores = []
        
        # Performance metrics
        total_processing_time = 0.0
        total_candidates_evaluated = 0
        
        # Match method distribution
        match_methods = {}
        tie_breaker_count = 0
        
        # Error analysis
        error_types = {}
        
        for result in results:
            # Confidence distribution
            confidence_dist[result.confidence_level] += 1
            confidence_scores.append(result.confidence_score)
            
            # Performance metrics
            total_processing_time += result.processing_time_ms
            total_candidates_evaluated += result.candidates_evaluated
            
            # Match methods
            method = result.match_method
            match_methods[method] = match_methods.get(method, 0) + 1
            
            # Tie breaker usage
            if hasattr(result, 'tie_breaker_used') and result.tie_breaker_used:
                tie_breaker_count += 1
            
            # Error analysis
            if not result.is_successful_match:
                if result.warnings:
                    error_type = result.warnings[0][:50]  # First 50 chars of first warning
                    error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Calculate averages
        avg_processing_time = total_processing_time / total_vehicles
        avg_candidates = total_candidates_evaluated / total_vehicles
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Calculate success rate
        success_rate = (successful_matches / total_vehicles * 100) if total_vehicles > 0 else 0
        
        # Data quality metrics
        excel_data_available = sum(1 for r in results 
                                 if r.extracted_attributes.has_excel_data)
        complete_attributes = sum(1 for r in results 
                                if r.extracted_attributes.completeness_score > 0.7)
        
        return {
            # Basic metrics
            'total_vehicles': total_vehicles,
            'successful_matches': successful_matches,
            'failed_matches': failed_matches,
            'success_rate': success_rate,
            
            # Confidence analysis
            'confidence_distribution': confidence_dist,
            'average_confidence_score': avg_confidence,
            'high_confidence_rate': (confidence_dist['high'] / total_vehicles * 100),
            
            # Performance metrics
            'performance_metrics': {
                'total_processing_time_ms': total_processing_time,
                'average_processing_time_ms': avg_processing_time,
                'average_candidates_evaluated': avg_candidates,
                'total_time_ms': total_time_ms,
                'throughput_vehicles_per_second': total_vehicles / (total_time_ms / 1000) if total_time_ms > 0 else 0
            },
            
            # Match method analysis
            'match_methods': match_methods,
            'tie_breaker_usage': {
                'ties_resolved': tie_breaker_count,
                'tie_breaker_rate': (tie_breaker_count / total_vehicles * 100)
            },
            
            # Data quality metrics
            'data_quality': {
                'excel_data_available': excel_data_available,
                'excel_data_rate': (excel_data_available / total_vehicles * 100),
                'complete_attributes': complete_attributes,
                'completeness_rate': (complete_attributes / total_vehicles * 100)
            },
            
            # Error analysis
            'error_analysis': {
                'error_types': error_types,
                'most_common_errors': sorted(error_types.items(), 
                                           key=lambda x: x[1], reverse=True)[:5]
            }
        }
    
    def _create_empty_summary(self) -> Dict[str, Any]:
        """Create empty summary for failed batches."""
        return {
            'total_vehicles': 0,
            'successful_matches': 0,
            'failed_matches': 0,
            'success_rate': 0.0,
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0, 'very_low': 0},
            'average_confidence_score': 0.0,
            'performance_metrics': {
                'total_processing_time_ms': 0.0,
                'average_processing_time_ms': 0.0,
                'average_candidates_evaluated': 0.0
            }
        }
    
    def _create_error_summary(self, error_message: str) -> Dict[str, Any]:
        """Create error summary."""
        summary = self._create_empty_summary()
        summary['batch_error'] = error_message
        return summary
    
    def _validate_batch(self, vehicles: List[Vehicle]) -> List[str]:
        """Validate entire batch before processing."""
        errors = []
        
        # Check batch size limits
        if len(vehicles) == 0:
            errors.append("Batch cannot be empty")
        
        if len(vehicles) > 1000:  # Reasonable batch size limit
            errors.append(f"Batch size {len(vehicles)} exceeds maximum (1000)")
        
        # Validate individual vehicles
        invalid_count = 0
        for i, vehicle in enumerate(vehicles):
            vehicle_errors = self.single_match_use_case.validate_input(vehicle)
            if vehicle_errors:
                invalid_count += 1
                if invalid_count <= 5:  # Report first 5 errors
                    errors.append(f"Vehicle {i}: {'; '.join(vehicle_errors)}")
        
        if invalid_count > 5:
            errors.append(f"Additional {invalid_count - 5} vehicles have validation errors")
        
        return errors
    
    async def get_progress_update(self, 
                                 vehicles: List[Vehicle],
                                 completed_results: List[MatchResult]) -> Dict[str, Any]:
        """Get progress update during batch processing."""
        
        completed_count = len(completed_results)
        total_count = len(vehicles)
        progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
        
        # Analyze completed results so far
        successful_so_far = sum(1 for r in completed_results if r.is_successful_match)
        current_success_rate = (successful_so_far / completed_count * 100) if completed_count > 0 else 0
        
        # Estimate remaining time based on current performance
        if completed_results:
            avg_time_per_vehicle = sum(r.processing_time_ms for r in completed_results) / completed_count
            estimated_remaining_time = avg_time_per_vehicle * (total_count - completed_count)
        else:
            estimated_remaining_time = 0.0
        
        return {
            'progress_percentage': progress_percentage,
            'completed_vehicles': completed_count,
            'total_vehicles': total_count,
            'remaining_vehicles': total_count - completed_count,
            'current_success_rate': current_success_rate,
            'successful_matches_so_far': successful_so_far,
            'estimated_remaining_time_ms': estimated_remaining_time
        }