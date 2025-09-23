"""Core business logic for vehicle codification."""

from .service import VehicleCodeifier
from .processor import VehicleProcessor

__all__ = ["VehicleCodeifier", "VehicleProcessor"]