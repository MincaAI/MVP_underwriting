"""
Document Transformer Service

Handles data transformation using broker profiles.
Integrates with the existing transform engine from worker-transform.
"""

import sys
import pathlib
import yaml
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "packages" / "profiles" / "src"))

from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import Run, Row, Transform, RunStatus, Component

logger = logging.getLogger(__name__)


class DocumentTransformer:
    """
    Transforms extracted data using broker-specific profiles.
    Applies validation rules, normalization, and computed fields.
    """
    
    def __init__(self):
        self.logger = logger
        self.profiles_path = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "configs" / "broker-profiles"
    
    async def transform(self, run_id: str, profile: str) -> Dict[str, Any]:
        """
        Transform extracted data using the specified broker profile.
        
        Args:
            run_id: Run identifier
            profile: Broker profile filename (e.g., 'lucky_gas.yaml')
            
        Returns:
            Transformation results with metrics
        """
        try:
            # Update run status
            with Session(engine) as session:
                run = session.get(Run, run_id)
                if not run:
                    raise ValueError(f"Run {run_id} not found")
                
                # Create transform component run
                transform_run = Run(
                    id=f"{run_id}_transform",
                    case_id=run.case_id,
                    component=Component.TRANSFORM,
                    status=RunStatus.STARTED,
                    parent_run_id=run_id,
                    started_at=datetime.utcnow()
                )
                session.add(transform_run)
                session.commit()
            
            # Load broker profile
            profile_config = await self._load_profile(profile)
            
            # Get extracted data
            extracted_rows = await self._get_extracted_data(run_id)
            
            # Transform data
            transformed_rows = []
            errors = []
            
            for row_data in extracted_rows:
                try:
                    transformed_row = await self._transform_row(row_data, profile_config)
                    transformed_rows.append(transformed_row)
                except Exception as e:
                    error_info = {
                        'row_id': row_data.get('id'),
                        'row_index': row_data.get('row_index'),
                        'error': str(e)
                    }
                    errors.append(error_info)
                    self.logger.warning(f"Error transforming row {row_data.get('row_index')}: {e}")
            
            # Store transformed data
            await self._store_transformed_data(transformed_rows, f"{run_id}_transform")
            
            # Calculate metrics
            metrics = {
                'total_rows': len(extracted_rows),
                'transformed_rows': len(transformed_rows),
                'error_rows': len(errors),
                'success_rate': len(transformed_rows) / len(extracted_rows) if extracted_rows else 0,
                'profile_used': profile,
                'errors': errors[:10]  # Store first 10 errors
            }
            
            # Update transform run with completion
            with Session(engine) as session:
                transform_run = session.get(Run, f"{run_id}_transform")
                transform_run.status = RunStatus.COMPLETED
                transform_run.completed_at = datetime.utcnow()
                transform_run.metrics = metrics
                session.commit()
            
            self.logger.info(f"Successfully transformed {len(transformed_rows)}/{len(extracted_rows)} rows using profile {profile}")
            return metrics
            
        except Exception as e:
            # Update run with error status
            with Session(engine) as session:
                transform_run = session.get(Run, f"{run_id}_transform")
                if transform_run:
                    transform_run.status = RunStatus.ERROR
                    transform_run.error_message = str(e)
                    session.commit()
            
            self.logger.error(f"Error transforming data for run {run_id}: {e}")
            raise
    
    async def _load_profile(self, profile: str) -> Dict[str, Any]:
        """Load broker profile configuration"""
        try:
            profile_path = self.profiles_path / profile
            
            if not profile_path.exists():
                # Use default generic profile
                profile_path = self.profiles_path / "generic.yaml"
                if not profile_path.exists():
                    # Return basic default configuration
                    return self._get_default_profile()
            
            with open(profile_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            return config
            
        except Exception as e:
            self.logger.warning(f"Error loading profile {profile}: {e}. Using default.")
            return self._get_default_profile()
    
    def _get_default_profile(self) -> Dict[str, Any]:
        """Get default transformation profile"""
        return {
            'name': 'Generic Profile',
            'description': 'Default transformation profile',
            'field_mappings': {
                'vehicle_id': 'vin',
                'vehicle_description': 'description',
                'vehicle_brand': 'brand',
                'vehicle_model': 'model',
                'vehicle_year': 'model_year',
                'license_plate': 'license_plate',
                'coverage_type': 'coverage_type',
                'insured_value': 'insured_value'
            },
            'validation_rules': {
                'vin': {'required': True, 'min_length': 17, 'max_length': 17},
                'model_year': {'required': True, 'min_value': 1900, 'max_value': 2025}
            },
            'computed_fields': {}
        }
    
    async def _get_extracted_data(self, run_id: str) -> List[Dict[str, Any]]:
        """Get extracted data from database"""
        try:
            with Session(engine) as session:
                rows = session.query(Row).filter(Row.run_id == run_id).all()
                
                extracted_data = []
                for row in rows:
                    row_data = row.extracted_data.copy() if row.extracted_data else {}
                    row_data.update({
                        'id': row.id,
                        'row_index': row.row_index,
                        'raw_data': row.raw_data
                    })
                    extracted_data.append(row_data)
                
                return extracted_data
                
        except Exception as e:
            self.logger.error(f"Error getting extracted data for run {run_id}: {e}")
            raise
    
    async def _transform_row(self, row_data: Dict[str, Any], profile_config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single row using the profile configuration"""
        transformed_row = {
            'id': row_data.get('id'),
            'row_index': row_data.get('row_index'),
            'run_id': row_data.get('run_id'),
            'transformed_at': datetime.utcnow().isoformat()
        }
        
        # Apply field mappings
        field_mappings = profile_config.get('field_mappings', {})
        for target_field, source_field in field_mappings.items():
            value = row_data.get(source_field)
            if value is not None:
                # Apply field-specific transformations
                transformed_value = await self._apply_field_transformation(value, target_field, profile_config)
                transformed_row[target_field] = transformed_value
        
        # Apply validation rules
        validation_errors = await self._validate_row(transformed_row, profile_config)
        transformed_row['validation_errors'] = validation_errors
        
        # Apply computed fields
        computed_fields = await self._compute_fields(transformed_row, profile_config)
        transformed_row.update(computed_fields)
        
        return transformed_row
    
    async def _apply_field_transformation(self, value: Any, field_name: str, profile_config: Dict[str, Any]) -> Any:
        """Apply field-specific transformations"""
        # Convert to string for processing
        str_value = str(value).strip() if value is not None else ""
        
        # Field-specific transformations
        if field_name in ['vehicle_year', 'model_year']:
            # Extract year from string if needed
            return self._extract_year(str_value)
        elif field_name in ['insured_value', 'premium', 'deductible']:
            # Parse currency values
            return self._parse_currency(str_value)
        elif field_name == 'vin':
            # Normalize VIN
            return self._normalize_vin(str_value)
        elif field_name == 'license_plate':
            # Normalize license plate
            return self._normalize_license_plate(str_value)
        else:
            # Default: clean and normalize
            return self._clean_text_value(str_value)
    
    def _extract_year(self, value: str) -> Optional[int]:
        """Extract year from text"""
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', value)
        if year_match:
            year = int(year_match.group())
            if 1900 <= year <= 2025:
                return year
        return None
    
    def _parse_currency(self, value: str) -> Optional[float]:
        """Parse currency value"""
        import re
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[^\d.,]', '', value)
        # Handle different decimal separators
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def _normalize_vin(self, vin: str) -> Optional[str]:
        """Normalize VIN format"""
        if not vin:
            return None
        # Remove spaces and convert to uppercase
        normalized = vin.replace(' ', '').upper()
        # Basic VIN validation (17 characters, alphanumeric except I, O, Q)
        if len(normalized) == 17 and normalized.replace('-', '').isalnum():
            return normalized
        return normalized  # Return as-is even if not valid format
    
    def _normalize_license_plate(self, plate: str) -> Optional[str]:
        """Normalize license plate format"""
        if not plate:
            return None
        # Remove extra spaces and convert to uppercase
        return ' '.join(plate.upper().split())
    
    def _clean_text_value(self, value: str) -> Optional[str]:
        """Clean and normalize text values"""
        if not value or value.lower() in ['nan', 'null', 'none', 'n/a', 'na']:
            return None
        # Clean extra whitespace
        return ' '.join(value.split())
    
    async def _validate_row(self, transformed_row: Dict[str, Any], profile_config: Dict[str, Any]) -> List[str]:
        """Validate transformed row against rules"""
        errors = []
        validation_rules = profile_config.get('validation_rules', {})
        
        for field, rules in validation_rules.items():
            value = transformed_row.get(field)
            
            # Required field validation
            if rules.get('required') and (value is None or value == ""):
                errors.append(f"{field} is required")
                continue
            
            if value is not None:
                # String length validation
                if 'min_length' in rules and len(str(value)) < rules['min_length']:
                    errors.append(f"{field} must be at least {rules['min_length']} characters")
                if 'max_length' in rules and len(str(value)) > rules['max_length']:
                    errors.append(f"{field} must be at most {rules['max_length']} characters")
                
                # Numeric value validation
                if 'min_value' in rules:
                    try:
                        numeric_value = float(value)
                        if numeric_value < rules['min_value']:
                            errors.append(f"{field} must be at least {rules['min_value']}")
                    except (ValueError, TypeError):
                        pass
                
                if 'max_value' in rules:
                    try:
                        numeric_value = float(value)
                        if numeric_value > rules['max_value']:
                            errors.append(f"{field} must be at most {rules['max_value']}")
                    except (ValueError, TypeError):
                        pass
        
        return errors
    
    async def _compute_fields(self, transformed_row: Dict[str, Any], profile_config: Dict[str, Any]) -> Dict[str, Any]:
        """Compute additional fields based on configuration"""
        computed = {}
        computed_fields = profile_config.get('computed_fields', {})
        
        for field_name, computation in computed_fields.items():
            try:
                if computation.get('type') == 'concat':
                    # Concatenate fields
                    fields = computation.get('fields', [])
                    separator = computation.get('separator', ' ')
                    values = [str(transformed_row.get(f, '')) for f in fields if transformed_row.get(f)]
                    computed[field_name] = separator.join(values) if values else None
                
                elif computation.get('type') == 'constant':
                    # Set constant value
                    computed[field_name] = computation.get('value')
                
                elif computation.get('type') == 'calculation':
                    # Simple calculations (could be extended)
                    formula = computation.get('formula', '')
                    # This is a placeholder - would implement safe expression evaluation
                    computed[field_name] = None
                    
            except Exception as e:
                self.logger.warning(f"Error computing field {field_name}: {e}")
                computed[field_name] = None
        
        return computed
    
    async def _store_transformed_data(self, transformed_rows: List[Dict[str, Any]], transform_run_id: str):
        """Store transformed data in database"""
        try:
            with Session(engine) as session:
                for row_data in transformed_rows:
                    # Create Transform record
                    transform = Transform(
                        id=f"transform_{row_data.get('id')}",
                        run_id=transform_run_id,
                        row_id=row_data.get('id'),
                        transformed_data=row_data,
                        validation_errors=row_data.get('validation_errors', []),
                        created_at=datetime.utcnow()
                    )
                    session.add(transform)
                
                session.commit()
                self.logger.info(f"Stored {len(transformed_rows)} transformed rows for run {transform_run_id}")
                
        except Exception as e:
            self.logger.error(f"Error storing transformed data: {e}")
            raise