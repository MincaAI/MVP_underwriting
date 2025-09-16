#!/usr/bin/env python3
"""
Activate a catalog version by setting it as ACTIVE status.
Only one version can be ACTIVE at a time.
"""

import argparse
from sqlalchemy import create_engine, text


def run(version: str, dburl: str) -> None:
    """
    Activate a catalog version.

    Args:
        version: Catalog version to activate
        dburl: Database URL
    """
    eng = create_engine(dburl)

    with eng.begin() as cx:
        # Check if version exists and is EMBEDDED
        result = cx.execute(text(
            "SELECT status, rows_loaded FROM catalog_import WHERE version = :v"
        ), {"v": version}).fetchone()

        if not result:
            raise ValueError(f"Catalog version '{version}' not found")

        status, rows_loaded = result
        if status != 'EMBEDDED':
            raise ValueError(f"Catalog version '{version}' has status '{status}'. Must be 'EMBEDDED' to activate.")

        print(f"Activating catalog version: {version} ({rows_loaded} rows)")

        # Deactivate all other versions
        cx.execute(text(
            """
            UPDATE catalog_import
            SET status = 'EMBEDDED'
            WHERE status = 'ACTIVE'
            """
        ))

        # Activate the target version
        cx.execute(text(
            """
            UPDATE catalog_import
            SET status = 'ACTIVE'
            WHERE version = :v
            """
        ), {"v": version})

        # Verify activation
        active_count = cx.execute(text(
            "SELECT COUNT(*) FROM catalog_import WHERE status = 'ACTIVE'"
        )).scalar()

        if active_count != 1:
            raise RuntimeError(f"Expected 1 active version, found {active_count}")

    print(f"✅ Catalog version '{version}' is now ACTIVE")


def list_versions(dburl: str) -> None:
    """List all catalog versions and their status."""
    eng = create_engine(dburl)

    with eng.begin() as cx:
        rows = cx.execute(text(
            """
            SELECT version, status, rows_loaded, model_id, created_at
            FROM catalog_import
            ORDER BY created_at DESC
            """
        )).fetchall()

    if not rows:
        print("No catalog versions found")
        return

    print("Catalog Versions:")
    print("Version".ljust(20) + "Status".ljust(12) + "Rows".ljust(8) + "Model".ljust(20) + "Created")
    print("-" * 80)

    for version, status, rows_loaded, model_id, created_at in rows:
        status_display = f"[{status}]" if status == 'ACTIVE' else status
        rows_display = str(rows_loaded) if rows_loaded else "-"
        model_display = model_id[:18] + "..." if model_id and len(model_id) > 20 else (model_id or "-")
        created_display = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "-"

        print(f"{version:<20} {status_display:<12} {rows_display:<8} {model_display:<20} {created_display}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Activate catalog version")
    ap.add_argument("--db", required=True, help="Database URL")

    subparsers = ap.add_subparsers(dest="command", help="Commands")

    # Activate command
    activate_parser = subparsers.add_parser("activate", help="Activate a catalog version")
    activate_parser.add_argument("--version", required=True, help="Catalog version to activate")

    # List command
    list_parser = subparsers.add_parser("list", help="List all catalog versions")

    args = ap.parse_args()

    if args.command == "activate":
        run(args.version, args.db)
    elif args.command == "list":
        list_versions(args.db)
    else:
        ap.error("No command specified. Use 'activate' or 'list'")