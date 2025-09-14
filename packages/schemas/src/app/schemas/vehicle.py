from typing import Optional
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, validator, constr
import re

class ValuationType(str, Enum):
    """Vehicle valuation types"""
    COMERCIAL = "COMERCIAL"
    FACTURA = "FACTURA" 
    CONVENIDO = "CONVENIDO"
    LIBRO = "LIBRO"

class FuelType(str, Enum):
    """Vehicle fuel types"""
    GASOLINE = "GASOLINE"
    DIESEL = "DIESEL"
    HYBRID = "HYBRID"
    ELECTRIC = "ELECTRIC"
    GAS = "GAS"
    FLEX = "FLEX"

class UseType(str, Enum):
    """Vehicle use types"""
    PERSONAL = "PERSONAL"
    COMMERCIAL = "COMMERCIAL"
    PUBLIC_SERVICE = "PUBLIC_SERVICE"
    TAXI = "TAXI"
    UBER = "UBER"

class Coverage(str, Enum):
    """Insurance coverage types"""
    AMPLIA = "AMPLIA"
    LIMITADA = "LIMITADA"
    RC = "RC"  # Responsabilidad Civil
    BASIC = "BASIC"

class CanonicalVehicle(BaseModel):
    """
    Canonical vehicle schema with mandatory and optional fields.
    
    Based on the specification with synonyms support and validation.
    """
    
    # === MANDATORY FIELDS ===
    vin: constr(min_length=17, max_length=17) = Field(
        ..., 
        description="17-character alphanumeric VIN (Vehicle Identification Number)",
        example="3N1CK3CD8JL254182"
    )
    
    description: str = Field(
        ..., 
        description="Free description of the vehicle model",
        min_length=1,
        max_length=500
    )
    
    brand: str = Field(
        ..., 
        description="Vehicle manufacturer/brand",
        min_length=1,
        max_length=100
    )
    
    model_year: int = Field(
        ..., 
        description="Year of manufacture/model (YYYY)",
        ge=1900,
        le=2100
    )
    
    # === OPTIONAL FIELDS ===
    license_plate: Optional[constr(max_length=20)] = Field(
        None,
        description="Vehicle registration plate, uppercase, no spaces"
    )
    
    subbrand: Optional[str] = Field(
        None,
        description="Vehicle line/trim/version",
        max_length=100
    )
    
    unit_type: Optional[str] = Field(
        None,
        description="Operational category (e.g. TRACTO, CAMIONETA, AUTO)",
        max_length=50
    )
    
    use_type: Optional[UseType] = Field(
        None,
        description="Vehicle use type: personal/commercial/public service"
    )
    
    fuel_type: Optional[FuelType] = Field(
        None,
        description="Fuel type: gasoline/diesel/hybrid/electric"
    )
    
    valuation_type: Optional[ValuationType] = Field(
        None,
        description="Valuation type: COMERCIAL | FACTURA | CONVENIDO | LIBRO"
    )
    
    insured_value: Optional[float] = Field(
        None,
        description="Insured amount",
        ge=0
    )
    
    currency: Optional[constr(min_length=3, max_length=3)] = Field(
        None,
        description="Currency code (ISO 4217): MXN, USD, etc.",
        example="MXN"
    )
    
    coverage: Optional[Coverage] = Field(
        None,
        description="Insurance coverage/package type"
    )
    
    company_name: Optional[str] = Field(
        None,
        description="Name of the owning company",
        max_length=200
    )
    
    policy_start: Optional[date] = Field(
        None,
        description="Policy start date (ISO YYYY-MM-DD)"
    )
    
    policy_end: Optional[date] = Field(
        None,
        description="Policy end date (ISO YYYY-MM-DD)"
    )
    
    # === VALIDATION ===
    @validator('vin')
    def validate_vin(cls, v):
        """Validate VIN format - 17 alphanumeric characters"""
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', v.upper()):
            raise ValueError('VIN must be 17 alphanumeric characters (excluding I, O, Q)')
        return v.upper()
    
    @validator('license_plate')
    def validate_license_plate(cls, v):
        """Normalize license plate - uppercase, no spaces"""
        if v is not None:
            return re.sub(r'\s+', '', v.upper())
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code format"""
        if v is not None:
            return v.upper()
        return v
    
    @validator('policy_end')
    def validate_policy_dates(cls, v, values):
        """Ensure policy end date is after start date"""
        if v is not None and 'policy_start' in values and values['policy_start'] is not None:
            if v <= values['policy_start']:
                raise ValueError('Policy end date must be after start date')
        return v
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            date: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "vin": "3N1CK3CD8JL254182",
                "description": "TOYOTA YARIS SOL L 2020",
                "brand": "TOYOTA",
                "model_year": 2020,
                "license_plate": "ABC123",
                "subbrand": "YARIS",
                "unit_type": "AUTO",
                "use_type": "PERSONAL",
                "fuel_type": "GASOLINE",
                "valuation_type": "COMERCIAL",
                "insured_value": 250000.0,
                "currency": "MXN",
                "coverage": "AMPLIA",
                "policy_start": "2024-01-01",
                "policy_end": "2024-12-31"
            }
        }

# === SYNONYM MAPPINGS ===
# These can be used by transformation services to map various input field names
# to the canonical field names

VIN_SYNONYMS = [
    "no_serie", "numero_serie", "n°_serie", "num_serie", "serie", 
    "VIN", "chasis", "no.chasis", "no_chasis", "serial_number"
]

DESCRIPTION_SYNONYMS = [
    "descripcion", "descripcion_vehiculo", "descripción", "detalle", "modelo_descripcion"
]

BRAND_SYNONYMS = [
    "marca", "fabricante", "brand"
]

MODEL_YEAR_SYNONYMS = [
    "modelo", "mod", "año", "anio", "modelo_serie", "year", "model_year"
]

LICENSE_PLATE_SYNONYMS = [
    "placa", "serie", "placas", "matricula", "placas_vehiculo", 
    "registration", "patente"
]

SUBBRAND_SYNONYMS = [
    "submarca", "linea", "versión", "version", "trim"
]

UNIT_TYPE_SYNONYMS = [
    "tipo_unidad", "tipo_de_unidad", "clase", "clase_vehiculo", 
    "tipo_vehiculo", "body_type"
]

USE_TYPE_SYNONYMS = [
    "uso", "uso_vehiculo", "uso_comercial", "service_use", "tipo_valor_uso"
]

FUEL_TYPE_SYNONYMS = [
    "combustible", "tipo_combustible", "fuel"
]

VALUATION_TYPE_SYNONYMS = [
    "tipo_valor", "tipo_de_valor", "valor_tipo"
]

INSURED_VALUE_SYNONYMS = [
    "valor_vehiculo", "suma_asegurada", "valor", "valor_comercial", "valor_factura"
]

CURRENCY_SYNONYMS = [
    "moneda", "divisa"
]

COVERAGE_SYNONYMS = [
    "paquete", "cobertura", "plan", "package"
]

COMPANY_NAME_SYNONYMS = [
    "empresa", "razon_social", "cliente", "compañía"
]

POLICY_START_SYNONYMS = [
    "vigencia_inicio", "inicio_vigencia", "fecha_inicio", "effective_date"
]

POLICY_END_SYNONYMS = [
    "vigencia_fin", "fin_vigencia", "fecha_fin", "expiry_date"
]

# Combined mapping for easy lookup
FIELD_SYNONYMS = {
    "vin": VIN_SYNONYMS,
    "description": DESCRIPTION_SYNONYMS,
    "brand": BRAND_SYNONYMS,
    "model_year": MODEL_YEAR_SYNONYMS,
    "license_plate": LICENSE_PLATE_SYNONYMS,
    "subbrand": SUBBRAND_SYNONYMS,
    "unit_type": UNIT_TYPE_SYNONYMS,
    "use_type": USE_TYPE_SYNONYMS,
    "fuel_type": FUEL_TYPE_SYNONYMS,
    "valuation_type": VALUATION_TYPE_SYNONYMS,
    "insured_value": INSURED_VALUE_SYNONYMS,
    "currency": CURRENCY_SYNONYMS,
    "coverage": COVERAGE_SYNONYMS,
    "company_name": COMPANY_NAME_SYNONYMS,
    "policy_start": POLICY_START_SYNONYMS,
    "policy_end": POLICY_END_SYNONYMS,
}