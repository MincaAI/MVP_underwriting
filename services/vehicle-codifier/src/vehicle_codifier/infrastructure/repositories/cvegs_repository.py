"""CVEGS repository implementation for data access."""

import pandas as pd
from typing import List, Dict, Any, Optional
import structlog
from abc import ABC, abstractmethod

from ...domain.entities.cvegs_entry import CVEGSEntry
from ...domain.services.candidate_finder import ICVEGSRepository
from ..adapters.data_loader_adapter import IDataLoader

logger = structlog.get_logger()


class CVEGSRepository(ICVEGSRepository):
    """Concrete implementation of CVEGS data repository."""
    
    def __init__(self, data_loader: IDataLoader):
        self.data_loader = data_loader
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def find_by_brand_and_year(self, 
                              insurer_id: str,
                              brand: str, 
                              year: Optional[int] = None) -> List[CVEGSEntry]:
        """Find CVEGS entries by brand and year."""
        
        try:
            # Load dataset for insurer
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return []
            
            # Filter by brand
            brand_mask = dataset['brand'].str.upper() == brand.upper()
            filtered = dataset[brand_mask]
            
            # Filter by year if provided
            if year is not None:
                year_mask = filtered['actual_year'] == year
                filtered = filtered[year_mask]
            
            # Convert to domain entities
            entries = self._dataframe_to_entities(filtered)
            
            logger.debug("Found entries by brand/year",
                        insurer_id=insurer_id,
                        brand=brand,
                        year=year,
                        count=len(entries))
            
            return entries
            
        except Exception as e:
            logger.error("Error finding by brand/year",
                        insurer_id=insurer_id,
                        brand=brand,
                        year=year,
                        error=str(e))
            return []
    
    def find_by_criteria(self, 
                        insurer_id: str,
                        criteria: Dict[str, Any]) -> List[CVEGSEntry]:
        """Find CVEGS entries by multiple criteria."""
        
        try:
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return []
            
            filtered = dataset.copy()
            
            # Apply each criterion
            for key, value in criteria.items():
                if key == 'brand_prefix' and isinstance(value, str):
                    mask = filtered['brand'].str.upper().str.startswith(value.upper())
                    filtered = filtered[mask]
                
                elif key == 'year_range' and isinstance(value, tuple):
                    min_year, max_year = value
                    mask = (filtered['actual_year'] >= min_year) & (filtered['actual_year'] <= max_year)
                    filtered = filtered[mask]
                
                elif key == 'model_contains' and isinstance(value, str):
                    mask = filtered['model'].str.upper().str.contains(value.upper(), na=False)
                    filtered = filtered[mask]
                
                elif key in filtered.columns:
                    # Direct column matching
                    if isinstance(value, str):
                        mask = filtered[key].str.upper() == value.upper()
                    else:
                        mask = filtered[key] == value
                    filtered = filtered[mask]
            
            entries = self._dataframe_to_entities(filtered)
            
            logger.debug("Found entries by criteria",
                        insurer_id=insurer_id,
                        criteria=criteria,
                        count=len(entries))
            
            return entries
            
        except Exception as e:
            logger.error("Error finding by criteria",
                        insurer_id=insurer_id,
                        criteria=criteria,
                        error=str(e))
            return []
    
    def search_text(self, 
                   insurer_id: str,
                   search_text: str,
                   limit: int = 100) -> List[CVEGSEntry]:
        """Search CVEGS entries by text similarity."""
        
        try:
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return []
            
            # Prepare search terms
            search_terms = search_text.upper().split()
            
            if not search_terms:
                return []
            
            # Score each entry based on text similarity
            scores = []
            
            for idx, row in dataset.iterrows():
                # Create searchable text from multiple fields
                searchable_text = f"{row['brand']} {row['model']} {row['description']}".upper()
                
                if pd.notna(row['actual_year']):
                    searchable_text += f" {row['actual_year']}"
                
                # Calculate simple scoring based on term matches
                score = 0
                for term in search_terms:
                    if term in searchable_text:
                        score += 1
                
                # Bonus for exact matches
                if search_text.upper() in searchable_text:
                    score += len(search_terms)
                
                scores.append((idx, score))
            
            # Sort by score and limit results
            scores.sort(key=lambda x: x[1], reverse=True)
            
            # Filter out zero scores and apply limit
            top_indices = [idx for idx, score in scores[:limit] if score > 0]
            
            if not top_indices:
                return []
            
            # Get top results
            top_results = dataset.loc[top_indices]
            entries = self._dataframe_to_entities(top_results)
            
            logger.debug("Text search completed",
                        insurer_id=insurer_id,
                        search_text=search_text,
                        results_found=len(entries))
            
            return entries
            
        except Exception as e:
            logger.error("Error in text search",
                        insurer_id=insurer_id,
                        search_text=search_text,
                        error=str(e))
            return []
    
    def find_by_cvegs_code(self, 
                          insurer_id: str,
                          cvegs_code: str) -> Optional[CVEGSEntry]:
        """Find a specific CVEGS entry by code."""
        
        try:
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return None
            
            # Find exact match by CVEGS code
            mask = dataset['cvegs_code'] == cvegs_code
            matches = dataset[mask]
            
            if matches.empty:
                return None
            
            # Return first match (should be unique)
            entries = self._dataframe_to_entities(matches)
            return entries[0] if entries else None
            
        except Exception as e:
            logger.error("Error finding by CVEGS code",
                        insurer_id=insurer_id,
                        cvegs_code=cvegs_code,
                        error=str(e))
            return None
    
    def get_all_brands(self, insurer_id: str) -> List[str]:
        """Get all unique brands for an insurer."""
        
        try:
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return []
            
            brands = dataset['brand'].dropna().unique().tolist()
            brands.sort()
            
            return brands
            
        except Exception as e:
            logger.error("Error getting brands",
                        insurer_id=insurer_id,
                        error=str(e))
            return []
    
    def get_models_for_brand(self, 
                           insurer_id: str,
                           brand: str) -> List[str]:
        """Get all models for a specific brand."""
        
        try:
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return []
            
            brand_mask = dataset['brand'].str.upper() == brand.upper()
            brand_data = dataset[brand_mask]
            
            models = brand_data['model'].dropna().unique().tolist()
            models.sort()
            
            return models
            
        except Exception as e:
            logger.error("Error getting models for brand",
                        insurer_id=insurer_id,
                        brand=brand,
                        error=str(e))
            return []
    
    def get_years_for_brand_model(self, 
                                 insurer_id: str,
                                 brand: str,
                                 model: str) -> List[int]:
        """Get all years for a specific brand/model combination."""
        
        try:
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return []
            
            brand_mask = dataset['brand'].str.upper() == brand.upper()
            model_mask = dataset['model'].str.upper() == model.upper()
            combined_mask = brand_mask & model_mask
            
            filtered = dataset[combined_mask]
            years = filtered['actual_year'].dropna().unique().tolist()
            years = [int(year) for year in years if pd.notna(year)]
            years.sort()
            
            return years
            
        except Exception as e:
            logger.error("Error getting years for brand/model",
                        insurer_id=insurer_id,
                        brand=brand,
                        model=model,
                        error=str(e))
            return []
    
    def get_statistics(self, insurer_id: str) -> Dict[str, Any]:
        """Get repository statistics."""
        
        try:
            dataset = self._get_dataset(insurer_id)
            
            if dataset.empty:
                return {'total_entries': 0}
            
            stats = {
                'total_entries': len(dataset),
                'unique_brands': dataset['brand'].nunique(),
                'unique_models': dataset['model'].nunique(),
                'entries_with_year': dataset['actual_year'].notna().sum(),
                'year_range': {
                    'min_year': int(dataset['actual_year'].min()) if dataset['actual_year'].notna().any() else None,
                    'max_year': int(dataset['actual_year'].max()) if dataset['actual_year'].notna().any() else None
                },
                'data_completeness': {
                    'has_brand': (dataset['brand'].notna().sum() / len(dataset) * 100),
                    'has_model': (dataset['model'].notna().sum() / len(dataset) * 100),
                    'has_year': (dataset['actual_year'].notna().sum() / len(dataset) * 100),
                    'has_description': (dataset['description'].notna().sum() / len(dataset) * 100)
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error("Error getting statistics",
                        insurer_id=insurer_id,
                        error=str(e))
            return {'total_entries': 0, 'error': str(e)}
    
    def _get_dataset(self, insurer_id: str) -> pd.DataFrame:
        """Get dataset for insurer with caching."""
        
        # Check cache first
        if insurer_id in self._cache:
            return self._cache[insurer_id]
        
        # Load from data loader
        try:
            dataset = self.data_loader.load_dataset(insurer_id)
            
            # Cache the dataset
            self._cache[insurer_id] = dataset
            
            return dataset
            
        except Exception as e:
            logger.error("Failed to load dataset",
                        insurer_id=insurer_id,
                        error=str(e))
            return pd.DataFrame()  # Return empty DataFrame on error
    
    def _dataframe_to_entities(self, df: pd.DataFrame) -> List[CVEGSEntry]:
        """Convert DataFrame rows to CVEGSEntry domain entities."""
        
        entries = []
        
        for _, row in df.iterrows():
            try:
                # Handle NaN values
                actual_year = int(row['actual_year']) if pd.notna(row['actual_year']) else None
                
                entry = CVEGSEntry.from_dataset_row(
                    cvegs_code=str(row['cvegs_code']),
                    brand=str(row['brand']) if pd.notna(row['brand']) else '',
                    model=str(row['model']) if pd.notna(row['model']) else '',
                    description=str(row['description']) if pd.notna(row['description']) else '',
                    year_code=str(row.get('year_code', '')) if pd.notna(row.get('year_code')) else None,
                    actual_year=actual_year
                )
                
                entries.append(entry)
                
            except Exception as e:
                logger.warning("Failed to convert row to CVEGSEntry",
                             row_index=row.name,
                             error=str(e))
                continue
        
        return entries
    
    def clear_cache(self):
        """Clear the repository cache."""
        self._cache.clear()
        logger.info("Repository cache cleared")
    
    def warm_cache(self, insurer_ids: List[str]):
        """Warm up the cache for multiple insurers."""
        
        logger.info("Warming up repository cache", insurer_count=len(insurer_ids))
        
        for insurer_id in insurer_ids:
            try:
                self._get_dataset(insurer_id)
                logger.debug("Cache warmed for insurer", insurer_id=insurer_id)
            except Exception as e:
                logger.warning("Failed to warm cache for insurer", 
                             insurer_id=insurer_id,
                             error=str(e))