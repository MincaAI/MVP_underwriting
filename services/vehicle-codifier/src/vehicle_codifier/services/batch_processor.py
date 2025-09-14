import asyncio
import time
from typing import List, Dict, Any
import structlog

from ..config.settings import get_settings
from ..models.vehicle import VehicleInput, BatchMatchRequest, BatchMatchResponse, MatchResult
from .matcher import CVEGSMatcher

logger = structlog.get_logger()


class BatchProcessor:
    """Handles batch processing of vehicle matching requests."""
    
    def __init__(self):
        self.settings = get_settings()
        self.matcher = CVEGSMatcher()
    
    async def process_batch(self, request: BatchMatchRequest) -> BatchMatchResponse:
        """
        Process a batch of vehicle matching requests.
        
        Args:
            request: Batch request with list of vehicles
            
        Returns:
            BatchMatchResponse with results and summary
        """
        start_time = time.time()
        
        logger.info("Starting batch processing", 
                   vehicle_count=len(request.vehicles),
                   insurer_id=request.insurer_id,
                   parallel_processing=request.parallel_processing)
        
        try:
            # Initialize insurer data once for the batch
            await self.matcher.initialize_insurer(request.insurer_id)
            
            # Process vehicles
            if request.parallel_processing:
                results = await self._process_parallel(request.vehicles)
            else:
                results = await self._process_sequential(request.vehicles)
            
            # Calculate total processing time
            total_time = (time.time() - start_time) * 1000
            
            # Generate summary
            summary = self._generate_summary(results)
            
            response = BatchMatchResponse(
                results=results,
                summary=summary,
                total_processing_time_ms=total_time
            )
            
            logger.info("Batch processing completed",
                       vehicle_count=len(request.vehicles),
                       successful_matches=summary['successful_matches'],
                       total_time_ms=total_time,
                       avg_time_per_vehicle=total_time / len(request.vehicles))
            
            return response
            
        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            raise
    
    async def _process_parallel(self, vehicles: List[VehicleInput]) -> List[MatchResult]:
        """Enhanced parallel processing with chunking for optimal performance."""
        
        # Step 15: Batch Processing in Parallel - split large batches into chunks
        chunk_size = min(50, len(vehicles))  # Optimal chunk size for LLM API limits
        chunks = [vehicles[i:i+chunk_size] for i in range(0, len(vehicles), chunk_size)]
        
        logger.info("Processing batch in chunks", 
                   total_vehicles=len(vehicles),
                   chunks=len(chunks),
                   chunk_size=chunk_size)
        
        all_results = []
        
        # Process chunks sequentially to avoid overwhelming the LLM API
        for chunk_idx, chunk in enumerate(chunks):
            logger.debug("Processing chunk", chunk_index=chunk_idx, vehicles_in_chunk=len(chunk))
            
            chunk_results = await self._process_chunk_parallel(chunk)
            all_results.extend(chunk_results)
            
            # Small delay between chunks to respect rate limits
            if chunk_idx < len(chunks) - 1:
                await asyncio.sleep(0.1)
        
        return all_results
    
    async def _process_chunk_parallel(self, chunk: List[VehicleInput]) -> List[MatchResult]:
        """Process a chunk of vehicles in parallel with controlled concurrency."""
        
        # Create semaphore to limit concurrent requests within chunk
        semaphore = asyncio.Semaphore(min(10, self.settings.max_concurrent_requests))
        
        async def bounded_match(vehicle: VehicleInput) -> MatchResult:
            """Match a single vehicle with concurrency control."""
            async with semaphore:
                try:
                    return await self.matcher.match_vehicle(vehicle)
                except Exception as e:
                    logger.error("Failed to match vehicle in batch",
                               description=vehicle.description[:50],
                               source_row=getattr(vehicle, 'source_row', None),
                               error=str(e))
                    # Return error result instead of failing the whole batch
                    return self._create_batch_error_result(vehicle, str(e))
        
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
                final_results.append(
                    self._create_batch_error_result(chunk[i], str(result))
                )
            else:
                final_results.append(result)
        
        return final_results
    
    async def _process_sequential(self, vehicles: List[VehicleInput]) -> List[MatchResult]:
        """Process vehicles sequentially (for debugging or rate limiting)."""
        
        results = []
        
        for i, vehicle in enumerate(vehicles):
            try:
                logger.debug("Processing vehicle", index=i, description=vehicle.description)
                result = await self.matcher.match_vehicle(vehicle)
                results.append(result)
                
            except Exception as e:
                logger.error("Failed to match vehicle in sequential batch",
                           index=i,
                           description=vehicle.description,
                           error=str(e))
                results.append(self._create_batch_error_result(vehicle, str(e)))
        
        return results
    
    def _create_batch_error_result(self, vehicle: VehicleInput, error_message: str) -> MatchResult:
        """Create an enhanced error result for a failed vehicle match in batch."""
        from ..models.vehicle import VehicleAttributes
        
        # Create attributes from Excel data if available
        error_attributes = VehicleAttributes(
            brand=vehicle.brand,
            model=vehicle.model,
            year=vehicle.year,
            vin=vehicle.vin,
            coverage_package=vehicle.coverage_package
        )
        
        return MatchResult(
            cvegs_code="BATCH_ERROR",
            confidence_score=0.0,
            confidence_level="very_low",
            matched_brand=vehicle.brand or "",
            matched_model=vehicle.model or "",
            matched_year=vehicle.year,
            matched_description="Batch processing error",
            extracted_attributes=error_attributes,
            processing_time_ms=0.0,
            candidates_evaluated=0,
            match_method="batch_error",
            attribute_matches=None,
            tie_breaker_used=False,
            source_row=vehicle.source_row,
            warnings=[f"Batch processing error: {error_message}"]
        )
    
    def _generate_summary(self, results: List[MatchResult]) -> Dict[str, Any]:
        """Generate summary statistics for batch results."""
        
        total_vehicles = len(results)
        successful_matches = 0
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0
        very_low_confidence = 0
        failed_matches = 0
        
        total_processing_time = 0.0
        total_candidates_evaluated = 0
        
        confidence_scores = []
        
        for result in results:
                # Count by confidence level
            if result.confidence_level == "high":
                high_confidence += 1
                successful_matches += 1
            elif result.confidence_level == "medium":
                medium_confidence += 1
                successful_matches += 1
            elif result.confidence_level == "low":
                low_confidence += 1
                successful_matches += 1
            else:
                very_low_confidence += 1
            
            # Check for errors or no matches
            if result.cvegs_code in ["ERROR", "BATCH_ERROR", "NO_MATCH"]:
                failed_matches += 1
                # Don't count failed matches as successful
                if result.confidence_level in ["high", "medium", "low"]:
                    successful_matches -= 1
            
            # Aggregate metrics
            total_processing_time += result.processing_time_ms
            total_candidates_evaluated += result.candidates_evaluated
            confidence_scores.append(result.confidence_score)
        
        # Calculate averages
        avg_processing_time = total_processing_time / total_vehicles if total_vehicles > 0 else 0
        avg_candidates = total_candidates_evaluated / total_vehicles if total_vehicles > 0 else 0
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Count match methods and tie-breaker usage
        match_methods = {}
        tie_breaker_count = 0
        
        for result in results:
            method = result.match_method
            match_methods[method] = match_methods.get(method, 0) + 1
            
            if hasattr(result, 'tie_breaker_used') and result.tie_breaker_used:
                tie_breaker_count += 1
        
        return {
            "total_vehicles": total_vehicles,
            "successful_matches": successful_matches,
            "failed_matches": failed_matches,
            "confidence_distribution": {
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "low_confidence": low_confidence,
                "very_low_confidence": very_low_confidence
            },
            "performance_metrics": {
                "total_processing_time_ms": total_processing_time,
                "average_processing_time_ms": avg_processing_time,
                "average_candidates_evaluated": avg_candidates,
                "average_confidence_score": avg_confidence
            },
            "match_methods": match_methods,
            "tie_breaker_usage": {
                "ties_resolved": tie_breaker_count,
                "tie_breaker_rate": (tie_breaker_count / total_vehicles * 100) if total_vehicles > 0 else 0
            },
            "success_rate": (successful_matches / total_vehicles * 100) if total_vehicles > 0 else 0
        }
    
    async def process_single_batch_item(self, vehicle: VehicleInput) -> MatchResult:
        """
        Process a single vehicle (used for testing or single requests).
        
        Args:
            vehicle: Single vehicle input
            
        Returns:
            MatchResult for the vehicle
        """
        try:
            return await self.matcher.match_vehicle(vehicle)
        except Exception as e:
            logger.error("Failed to process single vehicle", 
                        description=vehicle.description,
                        error=str(e))
            return self._create_batch_error_result(vehicle, str(e))
    
    def validate_batch_request(self, request: BatchMatchRequest) -> List[str]:
        """
        Validate batch request and return any validation errors.
        
        Args:
            request: Batch request to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check batch size
        if len(request.vehicles) > self.settings.max_batch_size:
            errors.append(f"Batch size {len(request.vehicles)} exceeds maximum {self.settings.max_batch_size}")
        
        if len(request.vehicles) == 0:
            errors.append("Batch cannot be empty")
        
        # Check individual vehicles
        for i, vehicle in enumerate(request.vehicles):
            if not vehicle.description or not vehicle.description.strip():
                errors.append(f"Vehicle {i}: Description cannot be empty")
            
            if len(vehicle.description) > 1000:  # Reasonable limit
                errors.append(f"Vehicle {i}: Description too long (max 1000 characters)")
        
        # Check insurer ID
        if not request.insurer_id or not request.insurer_id.strip():
            errors.append("Insurer ID cannot be empty")
        
        return errors
    
    async def get_batch_stats(self) -> Dict[str, Any]:
        """Get statistics about batch processing performance."""
        
        # This would typically come from a database or metrics store
        # For now, return basic system stats
        return {
            "max_batch_size": self.settings.max_batch_size,
            "max_concurrent_requests": self.settings.max_concurrent_requests,
            "request_timeout": self.settings.request_timeout,
            "system_status": "healthy"
        }
