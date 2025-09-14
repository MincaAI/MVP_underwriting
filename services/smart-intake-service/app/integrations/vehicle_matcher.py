from typing import List, Dict, Any, Optional
import httpx
import structlog
from datetime import datetime

from ..config.settings import get_settings

logger = structlog.get_logger()


class VehicleMatcherClient:
    """Client for integrating with the Vehicle CVEGS Matcher Service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.vehicle_matcher_url
        self.timeout = httpx.Timeout(self.settings.vehicle_matching_timeout)
    
    async def match_single_vehicle(self, vehicle_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match a single vehicle description to CVEGS code.
        
        Args:
            vehicle_input: Vehicle input data
            
        Returns:
            Match result from vehicle matcher service
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/match/single",
                    json=vehicle_input,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                result = response.json()
                
                logger.info("Single vehicle matched successfully", 
                           description=vehicle_input.get("description", "")[:50],
                           cvegs_code=result.get("cvegs_code"),
                           confidence=result.get("confidence_score"))
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error("Vehicle matcher API error", 
                        status_code=e.response.status_code,
                        description=vehicle_input.get("description", "")[:50],
                        error=str(e))
            raise
        except httpx.RequestError as e:
            logger.error("Vehicle matcher connection error", 
                        description=vehicle_input.get("description", "")[:50],
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error calling vehicle matcher", 
                        description=vehicle_input.get("description", "")[:50],
                        error=str(e))
            raise
    
    async def match_batch_vehicles(self, vehicle_inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Match multiple vehicle descriptions to CVEGS codes.
        
        Args:
            vehicle_inputs: List of vehicle input data
            
        Returns:
            Batch match results from vehicle matcher service
        """
        try:
            batch_request = {
                "vehicles": vehicle_inputs,
                "insurer_id": "default",
                "parallel_processing": True
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/match/batch",
                    json=batch_request,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                result = response.json()
                
                logger.info("Batch vehicles matched successfully", 
                           vehicle_count=len(vehicle_inputs),
                           successful_matches=result.get("summary", {}).get("successful_matches", 0),
                           success_rate=result.get("summary", {}).get("success_rate", 0))
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error("Vehicle matcher batch API error", 
                        status_code=e.response.status_code,
                        vehicle_count=len(vehicle_inputs),
                        error=str(e))
            raise
        except httpx.RequestError as e:
            logger.error("Vehicle matcher batch connection error", 
                        vehicle_count=len(vehicle_inputs),
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error calling vehicle matcher batch", 
                        vehicle_count=len(vehicle_inputs),
                        error=str(e))
            raise
    
    async def check_health(self) -> bool:
        """
        Check if vehicle matcher service is healthy.
        
        Returns:
            True if service is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers()
                )
                
                is_healthy = response.status_code == 200
                
                if is_healthy:
                    health_data = response.json()
                    logger.debug("Vehicle matcher health check passed", 
                               health_data=health_data)
                else:
                    logger.warning("Vehicle matcher health check failed", 
                                 status_code=response.status_code)
                
                return is_healthy
                
        except Exception as e:
            logger.error("Vehicle matcher health check error", error=str(e))
            return False
    
    async def get_service_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get statistics from vehicle matcher service.
        
        Returns:
            Service statistics or None if unavailable
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(
                    f"{self.base_url}/metrics",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                stats = response.json()
                
                logger.debug("Vehicle matcher stats retrieved", 
                           dataset_records=stats.get("dataset_stats", {}).get("default", {}).get("records", 0))
                
                return stats
                
        except Exception as e:
            logger.warning("Failed to get vehicle matcher stats", error=str(e))
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for service requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{self.settings.app_name}/{self.settings.app_version}"
        }
        
        # Add internal API key if configured
        if self.settings.internal_api_key:
            headers["X-API-Key"] = self.settings.internal_api_key
        
        return headers
    
    async def match_vehicles_with_retry(self, 
                                      vehicle_inputs: List[Dict[str, Any]],
                                      max_retries: int = 3) -> Dict[str, Any]:
        """
        Match vehicles with automatic retry logic.
        
        Args:
            vehicle_inputs: List of vehicle input data
            max_retries: Maximum number of retry attempts
            
        Returns:
            Match results with retry information
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if len(vehicle_inputs) == 1:
                    result = await self.match_single_vehicle(vehicle_inputs[0])
                    # Convert single result to batch format
                    return {
                        "results": [result],
                        "summary": {
                            "total_vehicles": 1,
                            "successful_matches": 1 if result.get("cvegs_code") not in ["NO_MATCH", "ERROR"] else 0,
                            "success_rate": 100.0 if result.get("cvegs_code") not in ["NO_MATCH", "ERROR"] else 0.0
                        }
                    }
                else:
                    return await self.match_batch_vehicles(vehicle_inputs)
                    
            except Exception as e:
                last_error = e
                
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning("Vehicle matching failed, retrying", 
                                 attempt=attempt + 1,
                                 max_retries=max_retries,
                                 retry_delay=retry_delay,
                                 error=str(e))
                    
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Vehicle matching failed after all retries", 
                               attempts=max_retries + 1,
                               final_error=str(e))
        
        # If all retries failed, return error result
        return {
            "results": [
                {
                    "cvegs_code": "ERROR",
                    "confidence_score": 0.0,
                    "error": str(last_error),
                    "description": vehicle_input.get("description", "")
                }
                for vehicle_input in vehicle_inputs
            ],
            "summary": {
                "total_vehicles": len(vehicle_inputs),
                "successful_matches": 0,
                "success_rate": 0.0,
                "error": str(last_error)
            }
        }
