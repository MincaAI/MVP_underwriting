#!/usr/bin/env python3
"""
Run the simplified vehicle codifier service.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import uvicorn
from vehicle_codifier.main import app
from vehicle_codifier.config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    print("🚀 Starting Vehicle Codifier Service")
    print(f"   Version: {settings.app_version}")
    print(f"   Port: 8002")
    print(f"   Debug: {settings.debug}")
    print(f"   Docs: http://localhost:8002/docs")
    print()

    uvicorn.run(
        "vehicle_codifier.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )