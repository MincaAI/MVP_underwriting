"""Dependency injection container for clean architecture."""

from typing import Dict, Any, Optional
import structlog

# Domain layer
from ..domain.services.attribute_extractor import AttributeExtractor
from ..domain.services.candidate_finder import CandidateFinder
from ..domain.services.scoring_engine import ScoringEngine
from ..domain.services.tie_breaker import TieBreaker
from ..domain.value_objects.match_criteria import MatchCriteria

# Application layer  
from ..application.use_cases.match_single_vehicle import MatchSingleVehicleUseCase
from ..application.use_cases.match_vehicle_batch import MatchVehicleBatchUseCase

# Infrastructure layer
from ..infrastructure.repositories.cvegs_repository import CVEGSRepository
from ..infrastructure.adapters.data_loader_adapter import DataLoaderAdapter
from ..infrastructure.adapters.llm_service_adapter import (
    LLMAttributeExtractorAdapter,
    PreprocessorAttributeExtractorAdapter,
    LLMTieBreakerService
)

# Configuration
from ..config.settings import get_settings

logger = structlog.get_logger()


class DIContainer:
    """Dependency injection container implementing the service locator pattern."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self.settings = get_settings()
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all services and their dependencies."""
        
        logger.info("Initializing dependency injection container")
        
        # Infrastructure adapters (singletons)
        self._register_singleton('data_loader_adapter', lambda: DataLoaderAdapter())
        self._register_singleton('llm_attribute_extractor', lambda: LLMAttributeExtractorAdapter())
        self._register_singleton('preprocessor_attribute_extractor', lambda: PreprocessorAttributeExtractorAdapter())
        self._register_singleton('llm_tie_breaker_service', lambda: LLMTieBreakerService())
        
        # Repositories (singletons)
        self._register_singleton('cvegs_repository', self._create_cvegs_repository)
        
        # Domain services (singletons)
        self._register_singleton('match_criteria', self._create_match_criteria)
        self._register_singleton('attribute_extractor', self._create_attribute_extractor)
        self._register_singleton('candidate_finder', self._create_candidate_finder)
        self._register_singleton('scoring_engine', self._create_scoring_engine)
        self._register_singleton('tie_breaker', self._create_tie_breaker)
        
        # Use cases (transient - new instance each time)
        self._register_transient('match_single_vehicle_use_case', self._create_match_single_vehicle_use_case)
        self._register_transient('match_vehicle_batch_use_case', self._create_match_vehicle_batch_use_case)
        
        logger.info("Dependency injection container initialized successfully")
    
    def _register_singleton(self, service_name: str, factory_func):
        """Register a singleton service."""
        self._services[service_name] = ('singleton', factory_func)
    
    def _register_transient(self, service_name: str, factory_func):
        """Register a transient service."""
        self._services[service_name] = ('transient', factory_func)
    
    def get(self, service_name: str) -> Any:
        """Get a service instance."""
        
        if service_name not in self._services:
            raise ValueError(f"Service '{service_name}' not registered")
        
        service_type, factory_func = self._services[service_name]
        
        if service_type == 'singleton':
            # Check if already created
            if service_name not in self._singletons:
                logger.debug("Creating singleton service", service_name=service_name)
                self._singletons[service_name] = factory_func()
            return self._singletons[service_name]
        
        elif service_type == 'transient':
            logger.debug("Creating transient service", service_name=service_name)
            return factory_func()
        
        else:
            raise ValueError(f"Unknown service type: {service_type}")
    
    def _create_cvegs_repository(self) -> CVEGSRepository:
        """Factory method for CVEGS repository."""
        data_loader_adapter = self.get('data_loader_adapter')
        return CVEGSRepository(data_loader_adapter)
    
    def _create_match_criteria(self) -> MatchCriteria:
        """Factory method for match criteria."""
        # Use default criteria or load from configuration
        if hasattr(self.settings, 'matching_criteria'):
            # Use custom criteria from settings
            criteria_config = self.settings.matching_criteria
            return MatchCriteria(**criteria_config)
        else:
            # Use default criteria
            return MatchCriteria()
    
    def _create_attribute_extractor(self) -> AttributeExtractor:
        """Factory method for attribute extractor."""
        preprocessor = self.get('preprocessor_attribute_extractor')
        llm_extractor = self.get('llm_attribute_extractor')
        return AttributeExtractor(preprocessor, llm_extractor)
    
    def _create_candidate_finder(self) -> CandidateFinder:
        """Factory method for candidate finder."""
        cvegs_repository = self.get('cvegs_repository')
        match_criteria = self.get('match_criteria')
        return CandidateFinder(cvegs_repository, match_criteria)
    
    def _create_scoring_engine(self) -> ScoringEngine:
        """Factory method for scoring engine."""
        match_criteria = self.get('match_criteria')
        return ScoringEngine(match_criteria)
    
    def _create_tie_breaker(self) -> TieBreaker:
        """Factory method for tie breaker."""
        llm_service = self.get('llm_tie_breaker_service')
        tie_threshold = getattr(self.settings, 'tie_threshold', 0.05)
        return TieBreaker(llm_service, tie_threshold)
    
    def _create_match_single_vehicle_use_case(self) -> MatchSingleVehicleUseCase:
        """Factory method for single vehicle matching use case."""
        return MatchSingleVehicleUseCase(
            attribute_extractor=self.get('attribute_extractor'),
            candidate_finder=self.get('candidate_finder'),
            scoring_engine=self.get('scoring_engine'),
            tie_breaker=self.get('tie_breaker'),
            match_criteria=self.get('match_criteria')
        )
    
    def _create_match_vehicle_batch_use_case(self) -> MatchVehicleBatchUseCase:
        """Factory method for batch vehicle matching use case."""
        single_match_use_case = self.get('match_single_vehicle_use_case')
        max_concurrent = getattr(self.settings, 'max_concurrent_requests', 10)
        chunk_size = getattr(self.settings, 'batch_chunk_size', 50)
        
        return MatchVehicleBatchUseCase(
            single_match_use_case,
            max_concurrent_requests=max_concurrent,
            chunk_size=chunk_size
        )
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about registered services."""
        
        service_info = {
            'registered_services': {},
            'singleton_instances': list(self._singletons.keys()),
            'total_registered': len(self._services)
        }
        
        for service_name, (service_type, _) in self._services.items():
            service_info['registered_services'][service_name] = {
                'type': service_type,
                'instantiated': service_name in self._singletons if service_type == 'singleton' else 'N/A'
            }
        
        return service_info
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services."""
        
        health_status = {
            'container_status': 'healthy',
            'services': {},
            'errors': []
        }
        
        critical_services = [
            'cvegs_repository',
            'attribute_extractor', 
            'candidate_finder',
            'scoring_engine',
            'tie_breaker'
        ]
        
        for service_name in critical_services:
            try:
                service = self.get(service_name)
                health_status['services'][service_name] = {
                    'status': 'healthy',
                    'type': type(service).__name__
                }
            except Exception as e:
                health_status['services'][service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['errors'].append(f"{service_name}: {str(e)}")
        
        if health_status['errors']:
            health_status['container_status'] = 'degraded'
        
        return health_status
    
    def warm_up(self):
        """Warm up critical singleton services."""
        
        logger.info("Warming up DI container services")
        
        critical_services = [
            'data_loader_adapter',
            'cvegs_repository',
            'attribute_extractor',
            'candidate_finder',
            'scoring_engine',
            'tie_breaker'
        ]
        
        for service_name in critical_services:
            try:
                self.get(service_name)
                logger.debug("Service warmed up", service_name=service_name)
            except Exception as e:
                logger.error("Failed to warm up service", 
                           service_name=service_name,
                           error=str(e))
        
        logger.info("DI container warm-up completed")
    
    def reset(self):
        """Reset the container (clear singletons)."""
        
        logger.warning("Resetting DI container - clearing all singleton instances")
        
        # Clear singleton instances
        self._singletons.clear()
        
        # Re-initialize
        self._initialize_services()


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container instance."""
    global _container
    
    if _container is None:
        _container = DIContainer()
    
    return _container


def reset_container():
    """Reset the global DI container."""
    global _container
    
    if _container is not None:
        _container.reset()
    else:
        _container = DIContainer()