#!/usr/bin/env python3
"""
Load AMIS Excel into Postgres (versioned), without embeddings.

Writes rows into:
- catalog_import (tracking)
- amis_catalog (catalog_version-scoped rows)
"""

import argparse
import os
import tempfile
import hashlib
from typing import List, Dict, Any
import pandas as pd
from unidecode import unidecode
from sqlalchemy import create_engine, text
import sys
import pathlib

# Add packages to path for S3 client
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "storage" / "src"))
from app.storage.s3 import download_to_tmp


def norm(s: Any) -> str:
    if s is None:
        return ""
    return unidecode(str(s).strip().lower())


def find_column(df: pd.DataFrame, *candidates: str) -> str:
    """Find column by trying multiple candidate names (case-insensitive)."""
    cols = {c.upper(): c for c in df.columns}
    for c in candidates:
        if c.upper() in cols:
            return cols[c.upper()]
    return None


def build_label(rec: dict) -> str:
    """
    Build structured label using CATVER column order, modelo (year) first.

    Format: modelo=<year> | marca=<brand> | submarca=<submarca> | ...
    Uses all CATVER columns except cvegs (already primary identifier).
    """
    parts = []

    # Start with modelo (year) first
    if rec.get("modelo"):
        parts.append(f"modelo={rec['modelo']}")

    # Add all other CATVER columns in order (except cvegs)
    if rec.get("marca"):
        parts.append(f"marca={norm(rec['marca'])}")
    if rec.get("submarca"):
        parts.append(f"submarca={norm(rec['submarca'])}")
    if rec.get("numver"):
        parts.append(f"numver={rec['numver']}")
    if rec.get("ramo"):
        parts.append(f"ramo={rec['ramo']}")
    if rec.get("cvemarc"):
        parts.append(f"cvemarc={rec['cvemarc']}")
    if rec.get("cvesubm"):
        parts.append(f"cvesubm={rec['cvesubm']}")
    if rec.get("martip"):
        parts.append(f"martip={rec['martip']}")
    if rec.get("cvesegm"):
        parts.append(f"cvesegm={norm(rec['cvesegm'])}")
    if rec.get("descveh"):
        parts.append(f"descveh={norm(rec['descveh'])}")
    if rec.get("idperdiod"):
        parts.append(f"idperdiod={rec['idperdiod']}")
    if rec.get("sumabas"):
        parts.append(f"sumabas={rec['sumabas']}")
    if rec.get("tipveh"):
        parts.append(f"tipveh={norm(rec['tipveh'])}")

    return " | ".join(parts)


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def run(version: str, s3_uri: str, dburl: str, xlsx_path: str = None) -> None:
    """
    Load catalog from S3 URI or local file path.

    Args:
        version: Catalog version identifier
        s3_uri: S3 URI to download from (s3://bucket/key)
        dburl: Database URL
        xlsx_path: Local file path (if not using S3)
    """
    eng = create_engine(dburl)

    # Download from S3 or use local file
    if s3_uri and s3_uri.startswith('s3://'):
        print(f"Downloading {s3_uri} to temporary file...")
        bucket = s3_uri.split('/')[2]
        key = '/'.join(s3_uri.split('/')[3:])

        temp_file = download_to_tmp(s3_uri)
        xlsx_path = temp_file
        print(f"Downloaded to {xlsx_path}")

        # Calculate SHA256 of downloaded file
        sha256 = calculate_sha256(xlsx_path)
        print(f"File SHA256: {sha256}")
    elif xlsx_path:
        # Use local file
        sha256 = calculate_sha256(xlsx_path) if os.path.exists(xlsx_path) else None
        print(f"Using local file: {xlsx_path}")
    else:
        raise ValueError("Either s3_uri or xlsx_path must be provided")

    df = pd.read_excel(xlsx_path)

    # Direct CATVER column mapping - all columns are required
    column_mapping = {
        'MARCA': find_column(df, 'MARCA'),
        'SUBMARCA': find_column(df, 'SUBMARCA'),
        'NUMVER': find_column(df, 'NUMVER'),
        'RAMO': find_column(df, 'RAMO'),
        'CVEMARC': find_column(df, 'CVEMARC'),
        'CVESUBM': find_column(df, 'CVESUBM'),
        'MARTIP': find_column(df, 'MARTIP'),
        'CVESEGM': find_column(df, 'CVESEGM'),
        'MODELO': find_column(df, 'MODELO'),  # Year in CATVER
        'CVEGS': find_column(df, 'CVEGS'),
        'DESCVEH': find_column(df, 'DESCVEH'),
        'IDPERDIOD': find_column(df, 'IDPERDIOD'),
        'SUMABAS': find_column(df, 'SUMABAS'),
        'TIPVEH': find_column(df, 'TIPVEH')
    }

    # Verify all required columns exist
    missing_cols = [key for key, val in column_mapping.items() if val is None]
    if missing_cols:
        raise ValueError(f"Missing required CATVER columns: {missing_cols}")

    print(f"Found CATVER columns: {list(column_mapping.values())}")

    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        try:
            rec = {
                "catalog_version": version,
                "marca": str(r[column_mapping['MARCA']]).strip(),
                "submarca": str(r[column_mapping['SUBMARCA']]).strip(),
                "numver": int(r[column_mapping['NUMVER']]) if pd.notna(r[column_mapping['NUMVER']]) else 0,
                "ramo": int(r[column_mapping['RAMO']]) if pd.notna(r[column_mapping['RAMO']]) else 0,
                "cvemarc": int(r[column_mapping['CVEMARC']]) if pd.notna(r[column_mapping['CVEMARC']]) else 0,
                "cvesubm": int(r[column_mapping['CVESUBM']]) if pd.notna(r[column_mapping['CVESUBM']]) else 0,
                "martip": int(r[column_mapping['MARTIP']]) if pd.notna(r[column_mapping['MARTIP']]) else 0,
                "cvesegm": str(r[column_mapping['CVESEGM']]).strip(),
                "modelo": int(r[column_mapping['MODELO']]) if pd.notna(r[column_mapping['MODELO']]) else 0,
                "cvegs": int(r[column_mapping['CVEGS']]) if pd.notna(r[column_mapping['CVEGS']]) else 0,
                "descveh": str(r[column_mapping['DESCVEH']]).strip(),
                "idperdiod": int(r[column_mapping['IDPERDIOD']]) if pd.notna(r[column_mapping['IDPERDIOD']]) else 0,
                "sumabas": float(str(r[column_mapping['SUMABAS']]).replace(',', '')) if pd.notna(r[column_mapping['SUMABAS']]) else 0.0,
                "tipveh": str(r[column_mapping['TIPVEH']]).strip(),
            }
            # Generate structured label
            rec["label"] = build_label(rec)
            rows.append(rec)
        except (ValueError, TypeError) as e:
            print(f"Warning: Skipping row {len(rows)+1} due to data conversion error: {e}")
            continue

    try:
        with eng.begin() as cx:
            # Always track the import with S3 URI and SHA256
            cx.execute(text(
                """
                INSERT INTO catalog_import(version,s3_uri,sha256,status)
                VALUES (:v,:u,:h,'UPLOADED')
                ON CONFLICT (version) DO UPDATE SET s3_uri=:u, sha256=:h, status='UPLOADED'
                """
            ), {"v": version, "u": s3_uri or "local", "h": sha256})

            # Clear existing data for this version
            cx.execute(text(
                "DELETE FROM amis_catalog WHERE catalog_version = :v"
            ), {"v": version})

            # Insert new data with CATVER schema including structured label
            cx.execute(text(
                """
                INSERT INTO amis_catalog(
                    catalog_version, marca, submarca, numver, ramo, cvemarc, cvesubm,
                    martip, cvesegm, modelo, cvegs, descveh, idperdiod, sumabas, tipveh, label
                )
                VALUES (
                    :catalog_version, :marca, :submarca, :numver, :ramo, :cvemarc, :cvesubm,
                    :martip, :cvesegm, :modelo, :cvegs, :descveh, :idperdiod, :sumabas, :tipveh, :label
                )
                """
            ), rows)

            # Mark as loaded
            cx.execute(text(
                "UPDATE catalog_import SET rows_loaded = :n, status='LOADED' WHERE version=:v"
            ), {"n": len(rows), "v": version})

        print(f"Loaded {len(rows)} rows into amis_catalog for version {version}")

    finally:
        # Clean up temporary file if downloaded from S3
        if s3_uri and s3_uri.startswith('s3://') and os.path.exists(xlsx_path):
            os.unlink(xlsx_path)
            print(f"Cleaned up temporary file: {xlsx_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Load AMIS catalog from S3 or local file")
    ap.add_argument("--version", required=True, help="Catalog version identifier")
    ap.add_argument("--s3-uri", help="S3 URI to download from (s3://bucket/key)")
    ap.add_argument("--file", help="Local Excel file path (alternative to S3)")
    ap.add_argument("--db", required=True, help="Database URL")

    args = ap.parse_args()

    if not args.s3_uri and not args.file:
        ap.error("Either --s3-uri or --file must be provided")

    run(args.version, args.s3_uri, args.db, args.file)


