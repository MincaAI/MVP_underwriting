"""
Database package for Minca AI Insurance Platform.

Provides SQLAlchemy models, session management, and Alembic migrations.
"""

from .base import Base
from .models import (
    # Core tables
    Case,
    Run,
    Row,
    Codify,
    Correction,
    # AMIS catalog
    AmisRecord,
    # Enums
    CaseStatus,
    Component,
    RunStatus,
)
from .session import get_session, SessionLocal, engine

__version__ = "0.1.0"

__all__ = [
    # Base
    "Base",
    # Models
    "Case",
    "Run", 
    "Row",
    "Codify",
    "Correction",
    "AmisRecord",
    # Enums
    "CaseStatus",
    "Component", 
    "RunStatus",
    # Session
    "get_session",
    "SessionLocal",
    "engine",
]
