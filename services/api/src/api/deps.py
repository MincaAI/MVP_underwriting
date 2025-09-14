"""
Dependency imports with compatibility for both Docker and local environments.
This module handles the workspace package import issues.
"""

import sys
import os
from pathlib import Path

# Detect if we're running in Docker or locally
def is_docker_environment():
    """Check if we're running in Docker container"""
    return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'

# Setup paths based on environment
if is_docker_environment():
    # Docker environment - packages are installed in system Python
    try:
        from app.db.session import get_session, get_db_session
        from app.db.models import Case, EmailMessage, EmailAttachment, Run, Component, RunStatus, Row
        from app.storage.s3 import upload_bytes
    except ImportError as e:
        print(f"Docker import failed: {e}")
        # Fallback to local path setup
        api_file = Path(__file__).resolve()
        api_dir = api_file.parent.parent.parent  # services/api
        project_root = api_dir.parent.parent  # project root
        
        paths_to_add = [
            str(project_root / "packages" / "db" / "src"),
            str(project_root / "packages" / "storage" / "src"),
            str(project_root / "packages" / "schemas" / "src"),
        ]
        
        for path in reversed(paths_to_add):
            if os.path.exists(path) and path not in sys.path:
                sys.path.insert(0, path)
        
        from app.db.session import get_session, get_db_session
        from app.db.models import Case, EmailMessage, EmailAttachment, Run, Component, RunStatus, Row
        from app.storage.s3 import upload_bytes
else:
    # Local development environment
    api_file = Path(__file__).resolve()
    api_dir = api_file.parent.parent.parent  # services/api
    project_root = api_dir.parent.parent  # project root
    
    # Add workspace packages to path at the very beginning
    paths_to_add = [
        str(project_root / "packages" / "db" / "src"),
        str(project_root / "packages" / "storage" / "src"),
        str(project_root / "packages" / "schemas" / "src"),
    ]
    
    # Force add paths at the beginning of sys.path for priority
    for path in reversed(paths_to_add):
        if os.path.exists(path):
            # Remove if exists and re-add at beginning
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(0, path)
    
    # Now import - the packages should be available
    from app.db.session import get_session, get_db_session
    from app.db.models import Case, EmailMessage, EmailAttachment, Run, Component, RunStatus, Row
    from app.storage.s3 import upload_bytes

# Re-export for use in other modules
__all__ = [
    'get_session',
    'get_db_session',
    'Case',
    'EmailMessage', 
    'EmailAttachment',
    'Run',
    'Row',
    'Component',
    'RunStatus',
    'upload_bytes'
]
