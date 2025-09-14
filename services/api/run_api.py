#!/usr/bin/env python
"""
Local API server launcher with proper path configuration.
This script fixes the workspace package import issues for local development.
"""

import sys
import os
from pathlib import Path

# Get the project root directory
api_dir = Path(__file__).parent
project_root = api_dir.parent.parent

# Add workspace packages to Python path
# These need to be added BEFORE importing anything else
sys.path.insert(0, str(project_root / "packages" / "db" / "src"))
sys.path.insert(0, str(project_root / "packages" / "storage" / "src"))
sys.path.insert(0, str(project_root / "packages" / "schemas" / "src"))
sys.path.insert(0, str(api_dir / "src"))

# Set environment variables
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://minca:minca@localhost:5432/minca")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("MINIO_ROOT_USER", "minio")
os.environ.setdefault("MINIO_ROOT_PASSWORD", "minio12345")
os.environ.setdefault("S3_BUCKET_RAW", "raw")
os.environ.setdefault("S3_BUCKET_EXPORTS", "exports")
os.environ.setdefault("S3_BUCKET", "mvp-underwriting")

# Import uvicorn and the app AFTER setting up paths
import uvicorn

if __name__ == "__main__":
    print("Starting API server with fixed paths...")
    print(f"Python path includes:")
    for p in sys.path[:5]:
        print(f"  - {p}")
    
    # Run the server
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(api_dir / "src")]
    )