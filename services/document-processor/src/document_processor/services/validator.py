"""
Document Validator Service

Provides comprehensive validation for extracted and transformed data.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentValidator:
    """
    Validates document data at various processing stages.
    Provides comprehensive validation rules and error reporting.
    """
    
    def __init__(self):
        self.logger = logger
    
    def validate_extracted_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate extracted data before transformation.
        
        Args:
            data: Extracted row data
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Check for completely empty row
            non_empty_fields = [v for v in data.values() if v is not None and str(v).strip()]
            if not non_empty_fields:
                errors.append("Row is completely empty")
                return False, errors
            
            # Basic field validation
            if 'vin' in data and data['vin']:
                vin_errors = self._validate_vin(data['vin'])
                errors.extend(vin_errors)
            
            if 'model_year' in data and data['model_year']:
                year_errors = self._validate_year(data['model_year'])
                errors.extend(year_errors)
            
            if 'license_plate' in data and data['license_plate']:
                plate_errors = self._validate_license_plate(data['license_plate'])
                errors.extend(plate_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating extracted data: {e}")
            return False, [f"Validation error: {e}"]
    
    def validate_transformed_data(self, data: Dict[str, Any], profile_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate transformed data against profile rules.
        
        Args:
            data: Transformed row data
            profile_config: Broker profile configuration
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Apply profile-specific validation rules
            validation_rules = profile_config.get('validation_rules', {})
            
            for field, rules in validation_rules.items():
                field_errors = self._validate_field(data.get(field), field, rules)
                errors.extend(field_errors)
            
            # Additional business logic validation
            business_errors = self._validate_business_rules(data)
            errors.extend(business_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating transformed data: {e}")
            return False, [f"Validation error: {e}"]
    
    def validate_export_data(self, data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate data before export.
        
        Args:
            data: List of rows to export
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            if not data:
                errors.append("No data to export")
                return False, errors
            
            # Check for duplicate VINs
            vins = [row.get('vin') for row in data if row.get('vin')]
            duplicate_vins = set([vin for vin in vins if vins.count(vin) > 1])
            if duplicate_vins:
                errors.append(f"Duplicate VINs found: {', '.join(duplicate_vins)}")
            
            # Check required fields for export
            required_export_fields = ['vin', 'description', 'brand']
            missing_required = []
            
            for i, row in enumerate(data):
                row_missing = [field for field in required_export_fields if not row.get(field)]
                if row_missing:
                    missing_required.append(f"Row {i+1}: {', '.join(row_missing)}")
            
            if missing_required:
                errors.extend([f"Missing required fields: {missing}" for missing in missing_required[:5]])  # Limit to first 5
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating export data: {e}")
            return False, [f"Validation error: {e}"]
    
    def _validate_vin(self, vin: str) -> List[str]:
        """Validate VIN format and content"""
        errors = []
        
        if not vin:
            return errors
        
        # Remove spaces and convert to uppercase
        clean_vin = str(vin).replace(' ', '').upper()
        
        # Basic length check
        if len(clean_vin) != 17:
            errors.append(f"VIN must be 17 characters (found {len(clean_vin)})")
            return errors
        
        # Character validation (no I, O, Q allowed)
        invalid_chars = set(clean_vin) & {'I', 'O', 'Q'}
        if invalid_chars:
            errors.append(f"VIN contains invalid characters: {', '.join(invalid_chars)}")
        
        # Alphanumeric check
        if not clean_vin.replace('-', '').isalnum():
            errors.append("VIN must contain only letters and numbers")
        
        return errors
    
    def _validate_year(self, year: Any) -> List[str]:
        """Validate vehicle year"""
        errors = []
        
        if not year:
            return errors
        
        try:
            year_int = int(float(str(year)))
            current_year = datetime.now().year
            
            if year_int < 1900:
                errors.append(f"Year {year_int} is too old (minimum: 1900)")
            elif year_int > current_year + 2:
                errors.append(f"Year {year_int} is in the future")
                
        except (ValueError, TypeError):
            errors.append(f"Invalid year format: {year}")
        
        return errors
    
    def _validate_license_plate(self, plate: str) -> List[str]:
        """Validate license plate format"""
        errors = []
        
        if not plate:
            return errors
        
        clean_plate = str(plate).strip()
        
        # Basic length check (most plates are 3-8 characters)
        if len(clean_plate) < 3 or len(clean_plate) > 10:
            errors.append(f"License plate length unusual: {len(clean_plate)} characters")
        
        # Check for suspicious patterns
        if clean_plate.lower() in ['n/a', 'na', 'none', 'null', 'test']:
            errors.append(f"Invalid license plate: {clean_plate}")
        
        return errors
    
    def _validate_field(self, value: Any, field_name: str, rules: Dict[str, Any]) -> List[str]:
        """Validate individual field against rules"""
        errors = []
        
        # Required field check
        if rules.get('required') and (value is None or str(value).strip() == ''):
            errors.append(f"{field_name} is required")
            return errors
        
        # Skip other validations if value is empty and not required
        if value is None or str(value).strip() == '':
            return errors
        
        str_value = str(value).strip()
        
        # String length validation
        if 'min_length' in rules and len(str_value) < rules['min_length']:
            errors.append(f"{field_name} must be at least {rules['min_length']} characters")
        
        if 'max_length' in rules and len(str_value) > rules['max_length']:
            errors.append(f"{field_name} must be at most {rules['max_length']} characters")
        
        # Numeric value validation
        if 'min_value' in rules or 'max_value' in rules:
            try:
                numeric_value = float(value)
                
                if 'min_value' in rules and numeric_value < rules['min_value']:
                    errors.append(f"{field_name} must be at least {rules['min_value']}")
                
                if 'max_value' in rules and numeric_value > rules['max_value']:
                    errors.append(f"{field_name} must be at most {rules['max_value']}")
                    
            except (ValueError, TypeError):
                if 'min_value' in rules or 'max_value' in rules:
                    errors.append(f"{field_name} must be a valid number")
        
        # Pattern validation
        if 'pattern' in rules:
            pattern = rules['pattern']
            if not re.match(pattern, str_value):
                errors.append(f"{field_name} does not match required pattern")
        
        # Allowed values validation
        if 'allowed_values' in rules:
            allowed = rules['allowed_values']
            if str_value not in allowed:
                errors.append(f"{field_name} must be one of: {', '.join(allowed)}")
        
        return errors
    
    def _validate_business_rules(self, data: Dict[str, Any]) -> List[str]:
        """Apply business logic validation rules"""
        errors = []
        
        # Insurance value should be reasonable
        insured_value = data.get('insured_value')
        if insured_value:
            try:
                value = float(insured_value)
                if value < 1000:
                    errors.append("Insured value seems too low (< $1,000)")
                elif value > 10000000:  # 10 million
                    errors.append("Insured value seems too high (> $10,000,000)")
            except (ValueError, TypeError):
                pass
        
        # Premium should be reasonable relative to insured value
        premium = data.get('premium')
        if premium and insured_value:
            try:
                prem_val = float(premium)
                ins_val = float(insured_value)
                ratio = prem_val / ins_val
                
                if ratio > 0.5:  # Premium > 50% of insured value
                    errors.append("Premium seems too high relative to insured value")
                elif ratio < 0.001:  # Premium < 0.1% of insured value
                    errors.append("Premium seems too low relative to insured value")
                    
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        
        # Year should make sense with brand/model
        year = data.get('model_year')
        brand = data.get('brand')
        if year and brand:
            try:
                year_int = int(float(str(year)))
                brand_str = str(brand).upper()
                
                # Tesla didn't exist before 2008
                if brand_str == 'TESLA' and year_int < 2008:
                    errors.append(f"Tesla did not manufacture vehicles in {year_int}")
                
            except (ValueError, TypeError):
                pass
        
        return errors