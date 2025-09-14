"""Data loader adapter interface and implementation."""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any
import structlog

from ...services.data_loader import DataLoader as LegacyDataLoader
from ...config.settings import get_insurer_config

logger = structlog.get_logger()


class IDataLoader(ABC):
    """Interface for data loading operations."""
    
    @abstractmethod
    def load_dataset(self, insurer_id: str) -> pd.DataFrame:
        """Load dataset for a specific insurer."""
        pass
    
    @abstractmethod
    def reload_dataset(self, insurer_id: str) -> pd.DataFrame:
        """Force reload dataset for a specific insurer."""
        pass


class DataLoaderAdapter(IDataLoader):
    """Adapter for the legacy data loader to implement the interface."""
    
    def __init__(self):
        self._legacy_loader = LegacyDataLoader()
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def load_dataset(self, insurer_id: str) -> pd.DataFrame:
        """Load dataset using legacy data loader."""
        
        # Check cache first
        if insurer_id in self._cache:
            logger.debug("Dataset loaded from cache", insurer_id=insurer_id)
            return self._cache[insurer_id]
        
        try:
            # Get insurer configuration
            insurer_config = get_insurer_config(insurer_id)
            
            # Load using legacy loader
            dataset = self._legacy_loader.load_dataset(insurer_config)
            
            # Validate dataset
            self._validate_dataset(dataset, insurer_id)
            
            # Cache the dataset
            self._cache[insurer_id] = dataset
            
            logger.info("Dataset loaded successfully",
                       insurer_id=insurer_id,
                       records=len(dataset))
            
            return dataset
            
        except Exception as e:
            logger.error("Failed to load dataset",
                        insurer_id=insurer_id,
                        error=str(e))
            # Return empty DataFrame instead of failing
            return pd.DataFrame()
    
    def reload_dataset(self, insurer_id: str) -> pd.DataFrame:
        """Force reload dataset, bypassing cache."""
        
        # Clear cache for this insurer
        if insurer_id in self._cache:
            del self._cache[insurer_id]
        
        logger.info("Forcing dataset reload", insurer_id=insurer_id)
        return self.load_dataset(insurer_id)
    
    def _validate_dataset(self, dataset: pd.DataFrame, insurer_id: str):
        """Validate loaded dataset structure."""
        
        required_columns = ['cvegs_code', 'brand', 'model', 'description']
        missing_columns = [col for col in required_columns if col not in dataset.columns]
        
        if missing_columns:
            raise ValueError(f"Dataset for {insurer_id} missing required columns: {missing_columns}")
        
        if dataset.empty:
            logger.warning("Loaded empty dataset", insurer_id=insurer_id)
        
        # Check for basic data quality
        null_counts = dataset[required_columns].isnull().sum()
        for col, null_count in null_counts.items():
            if null_count > 0:
                null_percentage = (null_count / len(dataset)) * 100
                if null_percentage > 50:
                    logger.warning(f"High null percentage in {col}",
                                 insurer_id=insurer_id,
                                 null_percentage=null_percentage)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached datasets."""
        
        cache_info = {}
        
        for insurer_id, dataset in self._cache.items():
            cache_info[insurer_id] = {
                'records': len(dataset),
                'memory_usage_mb': dataset.memory_usage(deep=True).sum() / (1024 * 1024),
                'columns': list(dataset.columns)
            }
        
        return {
            'cached_insurers': list(self._cache.keys()),
            'total_cached_datasets': len(self._cache),
            'details': cache_info
        }
    
    def clear_cache(self):
        """Clear all cached datasets."""
        self._cache.clear()
        logger.info("Data loader cache cleared")
    
    def clear_insurer_cache(self, insurer_id: str):
        """Clear cache for specific insurer."""
        if insurer_id in self._cache:
            del self._cache[insurer_id]
            logger.info("Cache cleared for insurer", insurer_id=insurer_id)