import re
import unicodedata
import pathlib
from typing import Dict, List, Optional
from unidecode import unidecode
import yaml

def load_abbreviations(path: Optional[pathlib.Path] = None) -> Dict[str, str]:
    """Load abbreviation mappings from YAML file."""
    if path is None:
        path = pathlib.Path(__file__).parent.parent.parent.parent.parent / "configs" / "aliases" / "abbreviations.yaml"
    
    try:
        if path.exists():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    
    # Default abbreviations for vehicle descriptions
    return {
        "a/c": "aire acondicionado",
        "ac": "aire acondicionado", 
        "abs": "sistema antibloqueo",
        "4x4": "traccion integral",
        "4wd": "traccion integral",
        "awd": "traccion integral",
        "fwd": "traccion delantera",
        "rwd": "traccion trasera",
        "cv": "caballos de fuerza",
        "hp": "caballos de fuerza",
        "bhp": "caballos de fuerza",
        "cc": "centimetros cubicos",
        "l": "litros",
        "v6": "motor v6",
        "v8": "motor v8",
        "v4": "motor v4",
        "std": "estandar",
        "std.": "estandar",
        "aut": "automatico",
        "auto": "automatico",
        "man": "manual",
        "mt": "transmision manual",
        "at": "transmision automatica",
        "cvt": "transmision variable continua",
        "dct": "transmision doble embrague",
        "pwr": "poder",
        "elec": "electrico",
        "gas": "gasolina",
        "dies": "diesel",
        "turbo": "turboalimentado",
        "hybrid": "hibrido",
        "phev": "hibrido enchufable",
        "bev": "electrico bateria",
        "ltd": "limitado",
        "lux": "lujo",
        "exec": "ejecutivo",
        "spt": "deportivo",
        "sport": "deportivo",
        "off": "fuera de carretera",
        "road": "carretera",
        "suv": "vehiculo utilitario deportivo",
        "mpv": "vehiculo multiproposito",
        "crossover": "cruzado",
        "hback": "hatchback",
        "conv": "convertible",
        "cab": "cabina",
        "ext": "extendida",
        "crew": "tripulacion",
        "reg": "regular",
        "dbl": "doble",
        "sgl": "individual",
        "2dr": "dos puertas",
        "4dr": "cuatro puertas", 
        "5dr": "cinco puertas",
        "w/": "con",
        "w/o": "sin",
        "pkg": "paquete",
        "equip": "equipamiento",
        "opt": "opcional",
        "trim": "version"
    }

def normalize_text(text: str, expand_abbreviations: bool = True, abbreviations: Optional[Dict[str, str]] = None) -> str:
    """
    Normalize text for consistent vehicle description matching.
    
    Args:
        text: Input text to normalize
        expand_abbreviations: Whether to expand common abbreviations
        abbreviations: Custom abbreviation mappings (loads default if None)
    
    Returns:
        Normalized text string
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Convert to lowercase and strip
    text = text.strip().lower()
    
    # Unicode normalization and remove diacritics
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    
    # Convert non-ASCII to ASCII approximations
    text = unidecode(text)
    
    # Remove special characters except spaces, hyphens, and periods
    text = re.sub(r"[^\w\s\-\.]", " ", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    # Expand abbreviations if requested
    if expand_abbreviations:
        if abbreviations is None:
            abbreviations = load_abbreviations()
        
        # Sort by length (longest first) to avoid partial replacements
        for abbrev, expansion in sorted(abbreviations.items(), key=lambda x: len(x[0]), reverse=True):
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(abbrev) + r"\b"
            text = re.sub(pattern, expansion, text)
    
    # Final cleanup
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def extract_vehicle_features(description: str) -> Dict[str, List[str]]:
    """
    Extract structured features from vehicle description.
    
    Args:
        description: Vehicle description text
        
    Returns:
        Dictionary with extracted features
    """
    normalized = normalize_text(description)
    
    features = {
        "transmission": [],
        "fuel_type": [],
        "drivetrain": [],
        "engine": [],
        "body_style": [],
        "features": []
    }
    
    # Transmission patterns
    transmission_patterns = {
        "manual": [r"\bmanual\b", r"\bmt\b", r"\btransmision manual\b"],
        "automatico": [r"\bautomatico\b", r"\bat\b", r"\btransmision automatica\b"],
        "cvt": [r"\bcvt\b", r"\btransmision variable continua\b"],
        "dct": [r"\bdct\b", r"\btransmision doble embrague\b"]
    }
    
    # Fuel type patterns  
    fuel_patterns = {
        "gasolina": [r"\bgasolina\b", r"\bgas\b", r"\bpetrol\b"],
        "diesel": [r"\bdiesel\b", r"\bdies\b"],
        "electrico": [r"\belectrico\b", r"\belectric\b", r"\bbev\b"],
        "hibrido": [r"\bhibrido\b", r"\bhybrid\b", r"\bphev\b"]
    }
    
    # Drivetrain patterns
    drivetrain_patterns = {
        "traccion_delantera": [r"\bfwd\b", r"\btraccion delantera\b"],
        "traccion_trasera": [r"\brwd\b", r"\btraccion trasera\b"],
        "traccion_integral": [r"\b4x4\b", r"\b4wd\b", r"\bawd\b", r"\btraccion integral\b"]
    }
    
    # Engine patterns
    engine_patterns = {
        "v4": [r"\bv4\b", r"\bmotor v4\b"],
        "v6": [r"\bv6\b", r"\bmotor v6\b"],
        "v8": [r"\bv8\b", r"\bmotor v8\b"],
        "turbo": [r"\bturbo\b", r"\bturboalimentado\b"]
    }
    
    # Body style patterns
    body_patterns = {
        "sedan": [r"\bsedan\b", r"\bcuatro puertas\b", r"\b4dr\b"],
        "hatchback": [r"\bhatchback\b", r"\bcinco puertas\b", r"\b5dr\b"],
        "suv": [r"\bsuv\b", r"\bvehiculo utilitario deportivo\b"],
        "pickup": [r"\bpickup\b", r"\bcamioneta\b"],
        "convertible": [r"\bconvertible\b", r"\bcabrio\b"],
        "coupe": [r"\bcoupe\b", r"\bdos puertas\b", r"\b2dr\b"]
    }
    
    # Extract features using patterns
    pattern_groups = [
        (transmission_patterns, "transmission"),
        (fuel_patterns, "fuel_type"),
        (drivetrain_patterns, "drivetrain"),
        (engine_patterns, "engine"),
        (body_patterns, "body_style")
    ]
    
    for patterns, feature_type in pattern_groups:
        for feature_name, regexes in patterns.items():
            for regex in regexes:
                if re.search(regex, normalized):
                    features[feature_type].append(feature_name)
                    break
    
    # Extract general features (air conditioning, abs, etc.)
    feature_keywords = [
        "aire acondicionado", "sistema antibloqueo", "direccion asistida",
        "asientos piel", "quemacocos", "rines aleacion", "faros niebla"
    ]
    
    for keyword in feature_keywords:
        if keyword in normalized:
            features["features"].append(keyword.replace(" ", "_"))
    
    return features