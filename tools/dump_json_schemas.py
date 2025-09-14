#!/usr/bin/env python3
"""
JSON Schema Export Tool

Generates JSON schemas from Pydantic models for frontend/API contracts.
Exports schemas to docs/schemas/ directory for documentation.

Usage:
    cd packages/schemas && poetry run python ../../tools/dump_json_schemas.py
"""

import json
import sys
from pathlib import Path

# Add the schemas package to Python path
current_dir = Path(__file__).parent.parent
schemas_src = current_dir / "packages" / "schemas" / "src"
if schemas_src.exists():
    sys.path.insert(0, str(schemas_src))

try:
    from app.schemas.core import CanonicalVehicleRow, CodifyResult, ExportSummary
    from app.schemas.vehicle import CanonicalVehicle, ValuationType, FuelType, UseType, Coverage
except ImportError as e:
    print(f"Error importing schemas: {e}")
    print("Make sure to run this script from packages/schemas with Poetry:")
    print("  cd packages/schemas && poetry run python ../../tools/dump_json_schemas.py")
    sys.exit(1)

def export_schemas():
    """Export all Pydantic schemas as JSON schemas"""
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "docs" / "schemas"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define schemas to export
    schemas = {
        "CanonicalVehicleRow": CanonicalVehicleRow,
        "CodifyResult": CodifyResult,
        "ExportSummary": ExportSummary,
        "CanonicalVehicle": CanonicalVehicle,
        "ValuationType": ValuationType,
        "FuelType": FuelType,
        "UseType": UseType,
        "Coverage": Coverage,
    }
    
    print(f"Exporting JSON schemas to {output_dir}")
    
    # Export each schema
    for name, schema_class in schemas.items():
        try:
            if hasattr(schema_class, 'model_json_schema'):
                # Pydantic v2 BaseModel
                json_schema = schema_class.model_json_schema()
            elif hasattr(schema_class, '__schema__'):
                # Enum or other types
                json_schema = {
                    "type": "string",
                    "enum": [item.value for item in schema_class] if hasattr(schema_class, '__members__') else []
                }
            else:
                print(f"Warning: Could not generate schema for {name}")
                continue
                
            # Write to file
            output_file = output_dir / f"{name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_schema, f, indent=2, ensure_ascii=False)
                
            print(f"  ✓ {name}.json")
            
        except Exception as e:
            print(f"  ✗ Error exporting {name}: {e}")
    
    # Create index file
    index_file = output_dir / "index.json"
    index_data = {
        "title": "Minca AI Insurance Platform - JSON Schemas",
        "version": "0.1.0",
        "description": "Canonical Pydantic schemas exported as JSON Schema",
        "schemas": list(schemas.keys()),
        "generated_at": "2024-01-01T00:00:00Z"  # You could use datetime.now().isoformat()
    }
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ index.json")
    print(f"\\nExported {len(schemas)} schemas successfully!")

if __name__ == "__main__":
    export_schemas()