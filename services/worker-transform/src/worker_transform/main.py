import uuid
import pandas as pd
import yaml
import sys
import pathlib

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "profiles" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "storage" / "src"))

from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import Run, Row, RunStatus, Component
from app.storage.s3 import download_to_tmp
from app.profiles.dsl import Profile
from app.profiles.runner import apply_profile

def process_transform(run_id: str, s3_uri: str, profile_path: str):
    """
    Process transformation of broker data using a profile.
    
    Args:
        run_id: Run identifier
        s3_uri: S3 URI of the source file
        profile_path: Path to the broker profile YAML
    """
    # Load profile
    with open(profile_path, "r", encoding="utf-8") as f:
        profile_data = yaml.safe_load(f)
    prof = Profile.model_validate(profile_data)
    
    # Download source file
    local_path = download_to_tmp(s3_uri)
    
    try:
        # Read Excel file (sheet detection can be added later)
        df = pd.read_excel(local_path)
        
        # Apply profile transformation
        df_transformed, report = apply_profile(df, prof)
        
        # Save results to database
        with Session(engine) as s:
            run = s.get(Run, run_id)
            assert run and run.component == Component.TRANSFORM, f"Invalid run {run_id} for TRANSFORM component"
            
            # Store transformed rows
            for i, row in df_transformed.reset_index(drop=True).iterrows():
                s.add(Row(
                    run_id=run_id, 
                    row_idx=int(i),
                    original={},  # Could store original row data here
                    transformed=row.to_dict(),
                    errors={},
                    warnings={}
                ))
            
            # Update run status and metrics
            run.status = RunStatus.SUCCESS
            run.metrics = report["metrics"]
            
            # Store validation errors if any
            if report.get("errors"):
                run.metrics["validation_errors"] = report["errors"]
            
            s.commit()
            
            print(f"Transform completed for run {run_id}")
            print(f"Processed {len(df_transformed)} rows")
            if report.get("errors"):
                print(f"Validation errors: {report['errors']}")
    
    finally:
        # Clean up temporary file
        import os
        os.unlink(local_path)