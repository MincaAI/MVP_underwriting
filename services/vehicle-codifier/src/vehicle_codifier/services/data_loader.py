import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import structlog
from pathlib import Path
import hashlib
import pickle
from datetime import datetime

from ..config.settings import get_settings, InsurerConfig

logger = structlog.get_logger()


class DataLoader:
    """Loads and manages CVEGS dataset from Excel files."""
    
    def __init__(self):
        self.settings = get_settings()
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.dataset_metadata: Dict[str, Dict] = {}
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self, dataset_path: str) -> Path:
        """Generate cache file path for dataset."""
        # Create hash of dataset path for cache filename
        path_hash = hashlib.md5(dataset_path.encode()).hexdigest()
        return self.cache_dir / f"dataset_{path_hash}.pkl"
    
    def _is_cache_valid(self, dataset_path: str, cache_path: Path) -> bool:
        """Check if cached dataset is still valid."""
        if not cache_path.exists():
            return False
        
        try:
            # Check if source file is newer than cache
            source_path = Path(dataset_path)
            if not source_path.exists():
                return False
            
            cache_mtime = cache_path.stat().st_mtime
            source_mtime = source_path.stat().st_mtime
            
            return cache_mtime > source_mtime
        except Exception as e:
            logger.warning("Error checking cache validity", error=str(e))
            return False
    
    def _load_from_cache(self, cache_path: Path) -> Optional[Tuple[pd.DataFrame, Dict]]:
        """Load dataset from cache."""
        try:
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
                return cached_data['dataframe'], cached_data['metadata']
        except Exception as e:
            logger.warning("Failed to load from cache", cache_path=str(cache_path), error=str(e))
            return None
    
    def _save_to_cache(self, cache_path: Path, dataframe: pd.DataFrame, metadata: Dict):
        """Save dataset to cache."""
        try:
            cached_data = {
                'dataframe': dataframe,
                'metadata': metadata,
                'cached_at': datetime.utcnow()
            }
            with open(cache_path, 'wb') as f:
                pickle.dump(cached_data, f)
            logger.info("Dataset cached successfully", cache_path=str(cache_path))
        except Exception as e:
            logger.warning("Failed to save to cache", cache_path=str(cache_path), error=str(e))
    
    def load_dataset(self, insurer_config: InsurerConfig) -> pd.DataFrame:
        """
        Load CVEGS dataset for a specific insurer.
        
        Args:
            insurer_config: Configuration for the insurer
            
        Returns:
            Loaded and processed DataFrame
        """
        dataset_path = insurer_config.dataset_path
        insurer_id = insurer_config.insurer_id
        
        # Check if already loaded
        if insurer_id in self.datasets:
            logger.info("Dataset already loaded", insurer_id=insurer_id)
            return self.datasets[insurer_id]
        
        # Check cache first
        cache_path = self._get_cache_path(dataset_path)
        if self._is_cache_valid(dataset_path, cache_path):
            cached_result = self._load_from_cache(cache_path)
            if cached_result:
                df, metadata = cached_result
                self.datasets[insurer_id] = df
                self.dataset_metadata[insurer_id] = metadata
                logger.info("Dataset loaded from cache", 
                           insurer_id=insurer_id, 
                           records=len(df))
                return df
        
        # Load from Excel file
        try:
            logger.info("Loading dataset from Excel", 
                       insurer_id=insurer_id, 
                       path=dataset_path)
            
            # Read Excel file
            df = pd.read_excel(dataset_path)
            
            # Process the dataset
            df = self._process_dataset(df, insurer_config)
            
            # Create metadata
            metadata = self._create_metadata(df, dataset_path)
            
            # Cache the processed dataset
            self._save_to_cache(cache_path, df, metadata)
            
            # Store in memory
            self.datasets[insurer_id] = df
            self.dataset_metadata[insurer_id] = metadata
            
            logger.info("Dataset loaded successfully", 
                       insurer_id=insurer_id,
                       records=len(df),
                       brands=df['brand'].nunique() if 'brand' in df.columns else 0)
            
            return df
            
        except FileNotFoundError:
            logger.error("Dataset file not found", path=dataset_path)
            raise
        except Exception as e:
            logger.error("Failed to load dataset", 
                        path=dataset_path, 
                        error=str(e))
            raise
    
    def _process_dataset(self, df: pd.DataFrame, insurer_config: InsurerConfig) -> pd.DataFrame:
        """
        Process and clean the dataset.
        
        Args:
            df: Raw DataFrame from Excel
            insurer_config: Insurer configuration
            
        Returns:
            Processed DataFrame
        """
        # Make a copy to avoid modifying original
        processed_df = df.copy()
        
        # Map Spanish column names to English
        column_mapping = insurer_config.column_mapping
        processed_df = processed_df.rename(columns=column_mapping)
        
        # Ensure required columns exist
        required_columns = ['brand', 'model', 'year_code', 'description', 'cvegs_code']
        missing_columns = [col for col in required_columns if col not in processed_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Clean and normalize data
        processed_df = self._clean_data(processed_df, insurer_config)
        
        # Add search indices
        processed_df = self._add_search_indices(processed_df)
        
        return processed_df
    
    def _clean_data(self, df: pd.DataFrame, insurer_config: InsurerConfig) -> pd.DataFrame:
        """Clean and normalize the dataset."""
        
        # Remove rows with missing essential data
        df = df.dropna(subset=['brand', 'model', 'cvegs_code'])
        
        # Normalize brand names using aliases
        brand_aliases = insurer_config.brand_aliases
        df['brand'] = df['brand'].astype(str).str.upper()
        df['brand'] = df['brand'].map(brand_aliases).fillna(df['brand'])
        
        # Normalize model names
        df['model'] = df['model'].astype(str).str.upper().str.strip()
        
        # Clean descriptions
        df['description'] = df['description'].astype(str).str.upper().str.strip()
        
        # Handle year codes (convert to actual years if needed)
        if insurer_config.year_code_mapping:
            df['actual_year'] = df['year_code'].map(insurer_config.year_code_mapping)
        else:
            # Assume year_code is already the actual year or needs conversion
            df['actual_year'] = self._convert_year_codes(df['year_code'])
        
        # Ensure CVEGS codes are strings
        df['cvegs_code'] = df['cvegs_code'].astype(str)
        
        # Remove duplicates based on key fields
        df = df.drop_duplicates(subset=['brand', 'model', 'year_code', 'description'])
        
        return df
    
    def _convert_year_codes(self, year_codes: pd.Series) -> pd.Series:
        """Convert year codes to actual years."""
        # This is a placeholder - you'll need to implement the actual conversion logic
        # based on your specific year coding system
        
        # For now, assume codes like 1401, 2002 need to be converted
        # This is just an example - adjust based on your actual data
        def convert_code(code):
            try:
                code = int(code)
                if code >= 1900 and code <= 2030:
                    return code  # Already a year
                elif code >= 1400 and code < 1500:
                    return 2000 + (code - 1400)  # Convert 1401 -> 2001
                elif code >= 2000 and code < 2100:
                    return 2000 + (code - 2000)  # Convert 2002 -> 2002
                else:
                    return None
            except:
                return None
        
        return year_codes.apply(convert_code)
    
    def _add_search_indices(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add search indices for faster matching."""
        
        # Create combined search text
        df['search_text'] = (
            df['brand'].astype(str) + ' ' +
            df['model'].astype(str) + ' ' +
            df['description'].astype(str)
        ).str.upper()
        
        # Create brand-year index for fast filtering
        df['brand_year'] = df['brand'].astype(str) + '_' + df['actual_year'].astype(str)
        
        # Create tokens for fuzzy matching
        df['tokens'] = df['search_text'].apply(lambda x: set(x.split()) if pd.notna(x) else set())
        
        return df
    
    def _create_metadata(self, df: pd.DataFrame, dataset_path: str) -> Dict:
        """Create metadata for the dataset."""
        return {
            'path': dataset_path,
            'loaded_at': datetime.utcnow(),
            'total_records': len(df),
            'unique_brands': df['brand'].nunique() if 'brand' in df.columns else 0,
            'unique_models': df['model'].nunique() if 'model' in df.columns else 0,
            'year_range': {
                'min': df['actual_year'].min() if 'actual_year' in df.columns else None,
                'max': df['actual_year'].max() if 'actual_year' in df.columns else None
            },
            'brands': df['brand'].unique().tolist() if 'brand' in df.columns else [],
            'columns': df.columns.tolist()
        }
    
    def get_dataset(self, insurer_id: str) -> Optional[pd.DataFrame]:
        """Get loaded dataset for insurer."""
        return self.datasets.get(insurer_id)
    
    def get_metadata(self, insurer_id: str) -> Optional[Dict]:
        """Get metadata for insurer dataset."""
        return self.dataset_metadata.get(insurer_id)
    
    def filter_candidates(self, 
                         insurer_id: str, 
                         brand: Optional[str] = None,
                         year: Optional[int] = None,
                         model: Optional[str] = None) -> pd.DataFrame:
        """
        Filter dataset to get candidate matches.
        
        Args:
            insurer_id: Insurer identifier
            brand: Brand to filter by
            year: Year to filter by
            model: Model to filter by
            
        Returns:
            Filtered DataFrame with candidates
        """
        df = self.get_dataset(insurer_id)
        if df is None:
            return pd.DataFrame()
        
        # Start with full dataset
        candidates = df.copy()
        
        # Filter by brand
        if brand:
            brand = brand.upper()
            candidates = candidates[candidates['brand'] == brand]
        
        # Filter by year
        if year:
            candidates = candidates[candidates['actual_year'] == year]
        
        # Filter by model (fuzzy match)
        if model:
            model = model.upper()
            # Exact match first
            exact_matches = candidates[candidates['model'] == model]
            if not exact_matches.empty:
                candidates = exact_matches
            else:
                # Fuzzy match - contains model name
                fuzzy_matches = candidates[candidates['model'].str.contains(model, na=False)]
                if not fuzzy_matches.empty:
                    candidates = fuzzy_matches
        
        return candidates
    
    def get_stats(self) -> Dict:
        """Get statistics about loaded datasets."""
        stats = {}
        for insurer_id, df in self.datasets.items():
            metadata = self.dataset_metadata.get(insurer_id, {})
            stats[insurer_id] = {
                'records': len(df),
                'brands': df['brand'].nunique() if 'brand' in df.columns else 0,
                'models': df['model'].nunique() if 'model' in df.columns else 0,
                'loaded_at': metadata.get('loaded_at'),
                'year_range': metadata.get('year_range')
            }
        return stats
