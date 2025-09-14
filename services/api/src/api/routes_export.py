from fastapi import APIRouter
import os
import sys
import pathlib

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "storage" / "src"))

# Add worker-exporter to path for imports  
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent / "worker-exporter" / "src"))

from worker_exporter.main import process_export

router = APIRouter(prefix="/export")

@router.post("")
def export(run_id: str, template: str = "configs/gcotiza-templates/gcotiza_v1.yaml"):
    """
    Export run data to Gcotiza Excel format.
    
    Args:
        run_id: Run identifier to export
        template: Export template YAML path
        
    Returns:
        Export result with download URL and metadata
    """
    # Get S3 configuration
    bucket = os.getenv("S3_BUCKET_EXPORTS", "exports")
    key_prefix = "gcotiza"
    
    # Process export
    result = process_export(run_id, template, bucket, key_prefix)
    
    return result

@router.get("/download")
def get_download_url(run_id: str, expiration: int = 3600):
    """
    Get presigned download URL for an exported file.
    
    Args:
        run_id: Run identifier
        expiration: URL expiration in seconds (default: 1 hour)
        
    Returns:
        Presigned download URL
    """
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.db.models import Export
    from app.storage.s3 import get_presigned_url, parse_s3_uri
    
    with Session(engine) as s:
        export_record = (
            s.query(Export)
             .filter(Export.run_id == run_id)
             .filter(Export.target == "Gcotiza")
             .order_by(Export.created_at.desc())
             .first()
        )
        
        if not export_record:
            return {"error": "Export not found for run"}
        
        # Parse S3 URI to get bucket and key
        bucket, key = parse_s3_uri(export_record.file_url)
        
        # Generate presigned URL
        download_url = get_presigned_url(bucket, key, expiration)
        
        return {
            "download_url": download_url,
            "expires_in": expiration,
            "checksum": export_record.checksum,
            "created_at": export_record.created_at.isoformat()
        }