"""
Document Extractor Service

Handles Excel/CSV file parsing and data extraction.
Migrated from doc2canon-service and worker-extractor.
"""

import sys
import pathlib
import pandas as pd
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from io import BytesIO
from fastapi import UploadFile

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "packages" / "storage" / "src"))

from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import Run, Row, RunStatus, Component
from app.storage.s3 import upload_bytes

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """
    Extracts data from Excel/CSV documents and stores in database.
    Combines robust parsing from doc2canon with async capabilities from worker-extractor.
    """
    
    def __init__(self):
        self.logger = logger
        
    async def extract(self, file: UploadFile, run_id: str, case_id: str) -> List[Dict[str, Any]]:
        """
        Extract data from uploaded file and store in database.
        
        Args:
            file: Uploaded file (Excel or CSV)
            run_id: Unique run identifier
            case_id: Case identifier
            
        Returns:
            List of extracted row data
        """
        try:
            # Read file content
            file_content = await file.read()
            
            # Create database run record
            with Session(engine) as session:
                run = Run(
                    id=run_id,
                    case_id=case_id,
                    component=Component.EXTRACT,
                    status=RunStatus.STARTED,
                    file_name=file.filename,
                    started_at=datetime.utcnow()
                )
                session.add(run)
                session.commit()
            
            # Parse file based on extension
            if file.filename.endswith('.csv'):
                df = await self._parse_csv(file_content)
            else:  # Excel files
                df = await self._parse_excel(file_content)
            
            # Extract and validate data
            extracted_rows = await self._extract_vehicle_data(df, run_id)
            
            # Store extracted data in database
            await self._store_extracted_data(extracted_rows, run_id)
            
            # Upload original file to S3
            s3_key = f"raw/{run_id}/{file.filename}"
            file_url = upload_bytes(file_content, s3_key)
            
            # Update run with completion
            with Session(engine) as session:
                run = session.get(Run, run_id)
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.utcnow()
                run.file_s3_uri = file_url
                run.metrics = {
                    "rows_extracted": len(extracted_rows),
                    "file_size": len(file_content)
                }
                session.commit()
            
            self.logger.info(f"Successfully extracted {len(extracted_rows)} rows from {file.filename}")
            return extracted_rows
            
        except Exception as e:
            # Update run with error status
            with Session(engine) as session:
                run = session.get(Run, run_id)
                if run:
                    run.status = RunStatus.ERROR
                    run.error_message = str(e)
                    session.commit()
            
            self.logger.error(f"Error extracting from {file.filename}: {e}")
            raise
    
    async def _parse_csv(self, file_content: bytes) -> pd.DataFrame:
        """Parse CSV file content"""
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    content_str = file_content.decode(encoding)
                    df = pd.read_csv(BytesIO(content_str.encode('utf-8')))
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode CSV file with any supported encoding")
                
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {e}")
    
    async def _parse_excel(self, file_content: bytes) -> pd.DataFrame:
        """Parse Excel file content"""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(BytesIO(file_content))
            
            # Use the first sheet by default
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(BytesIO(file_content), sheet_name=sheet_name)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to parse Excel file: {e}")
    
    async def _extract_vehicle_data(self, df: pd.DataFrame, run_id: str) -> List[Dict[str, Any]]:
        """
        Extract vehicle data from DataFrame using intelligent header mapping.
        Migrated from doc2canon service.
        """
        extracted_rows = []
        
        # Normalize column headers
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        # Map headers to standard fields
        header_mapping = self._get_header_mapping()
        
        for index, row in df.iterrows():
            try:
                # Extract vehicle data using mapped headers
                vehicle_data = {}
                
                for standard_field, possible_headers in header_mapping.items():
                    value = None
                    for header in possible_headers:
                        if header in df.columns:
                            raw_value = row[header]
                            if pd.notna(raw_value) and str(raw_value).strip():
                                value = self._clean_value(str(raw_value).strip())
                                break
                    
                    vehicle_data[standard_field] = value
                
                # Add metadata
                vehicle_data.update({
                    'row_index': index,
                    'run_id': run_id,
                    'extracted_at': datetime.utcnow().isoformat(),
                    'raw_data': row.to_dict()  # Store original row data
                })
                
                extracted_rows.append(vehicle_data)
                
            except Exception as e:
                self.logger.warning(f"Error processing row {index}: {e}")
                # Continue with other rows
                continue
        
        return extracted_rows
    
    def _get_header_mapping(self) -> Dict[str, List[str]]:
        """
        Get mapping from standard fields to possible Excel headers.
        Supports Spanish and English variations.
        """
        return {
            'vin': ['vin', 'numero_vin', 'numero vin', 'vin_number', 'chassis'],
            'description': ['description', 'descripcion', 'desc', 'vehicle_description'],
            'brand': ['brand', 'marca', 'make', 'fabricante'],
            'model': ['model', 'modelo', 'vehicle_model'],
            'model_year': ['year', 'año', 'model_year', 'año_modelo', 'anio'],
            'license_plate': ['plate', 'placa', 'license_plate', 'matricula', 'patente'],
            'coverage_type': ['coverage', 'cobertura', 'tipo_cobertura', 'coverage_type'],
            'insured_value': ['value', 'valor', 'suma_asegurada', 'insured_value', 'monto'],
            'premium': ['premium', 'prima', 'cost', 'costo'],
            'deductible': ['deductible', 'deducible', 'franquicia'],
            'color': ['color', 'colour'],
            'fuel_type': ['fuel', 'combustible', 'fuel_type', 'tipo_combustible'],
            'transmission': ['transmission', 'transmision', 'gear', 'cambio'],
            'doors': ['doors', 'puertas', 'door_count', 'numero_puertas'],
            'seats': ['seats', 'asientos', 'seat_count', 'numero_asientos'],
            'engine_size': ['engine', 'motor', 'engine_size', 'cilindraje'],
            'mileage': ['mileage', 'kilometraje', 'odometer', 'km']
        }
    
    def _clean_value(self, value: str) -> str:
        """Clean and normalize extracted values"""
        if not value or value.lower() in ['nan', 'null', 'none', '']:
            return None
            
        # Remove extra whitespace
        value = ' '.join(value.split())
        
        # Handle common data issues
        if value.lower() in ['n/a', 'na', 'no aplica', 'no disponible']:
            return None
            
        return value
    
    async def _store_extracted_data(self, extracted_rows: List[Dict[str, Any]], run_id: str):
        """Store extracted data in database"""
        try:
            with Session(engine) as session:
                for row_data in extracted_rows:
                    # Create Row record
                    row = Row(
                        id=f"{run_id}_{row_data['row_index']}",
                        run_id=run_id,
                        row_index=row_data['row_index'],
                        raw_data=row_data['raw_data'],
                        extracted_data=row_data,
                        created_at=datetime.utcnow()
                    )
                    session.add(row)
                
                session.commit()
                self.logger.info(f"Stored {len(extracted_rows)} rows for run {run_id}")
                
        except Exception as e:
            self.logger.error(f"Error storing extracted data: {e}")
            raise