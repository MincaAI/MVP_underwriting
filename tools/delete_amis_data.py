#!/usr/bin/env python3
"""
Delete data from amis_catalog table with safety options.

Provides options to:
- Delete all data from amis_catalog table
- Delete data for specific catalog version(s)
- Preview current data before deletion
"""

import argparse
from sqlalchemy import create_engine, text
import sys


def show_table_info(dburl: str) -> None:
    """Show current table statistics."""
    eng = create_engine(dburl)

    with eng.begin() as cx:
        # Total row count
        total_result = cx.execute(text("SELECT COUNT(*) FROM amis_catalog")).fetchone()
        total_rows = total_result[0] if total_result else 0

        # Version breakdown
        version_result = cx.execute(text(
            "SELECT catalog_version, COUNT(*) FROM amis_catalog GROUP BY catalog_version ORDER BY catalog_version"
        )).fetchall()

        print(f"📊 Current amis_catalog table status:")
        print(f"   Total rows: {total_rows}")

        if version_result:
            print(f"   Versions:")
            for version, count in version_result:
                print(f"     {version}: {count} rows")
        else:
            print("   No data found in table")


def delete_all_data(dburl: str, force: bool = False) -> None:
    """Delete all data from amis_catalog table."""
    eng = create_engine(dburl)

    if not force:
        show_table_info(dburl)
        print("\n⚠️  WARNING: This will delete ALL data from amis_catalog table!")
        confirm = input("Type 'DELETE ALL' to confirm: ")
        if confirm != "DELETE ALL":
            print("❌ Operation cancelled")
            return

    with eng.begin() as cx:
        result = cx.execute(text("DELETE FROM amis_catalog"))
        print(f"✅ Deleted {result.rowcount} rows from amis_catalog table")


def delete_version_data(dburl: str, version: str, force: bool = False) -> None:
    """Delete data for specific catalog version."""
    eng = create_engine(dburl)

    # Check if version exists
    with eng.begin() as cx:
        count_result = cx.execute(text(
            "SELECT COUNT(*) FROM amis_catalog WHERE catalog_version = :v"
        ), {"v": version}).fetchone()

        if not count_result or count_result[0] == 0:
            print(f"❌ No data found for version '{version}'")
            return

        row_count = count_result[0]

        if not force:
            print(f"📊 Found {row_count} rows for version '{version}'")
            print(f"⚠️  WARNING: This will delete {row_count} rows for version '{version}'")
            confirm = input(f"Type 'DELETE {version}' to confirm: ")
            if confirm != f"DELETE {version}":
                print("❌ Operation cancelled")
                return

        result = cx.execute(text(
            "DELETE FROM amis_catalog WHERE catalog_version = :v"
        ), {"v": version})

        print(f"✅ Deleted {result.rowcount} rows for version '{version}'")


def list_versions(dburl: str) -> None:
    """List all available catalog versions."""
    eng = create_engine(dburl)

    with eng.begin() as cx:
        result = cx.execute(text(
            "SELECT catalog_version, COUNT(*) FROM amis_catalog GROUP BY catalog_version ORDER BY catalog_version"
        )).fetchall()

        if result:
            print("📝 Available catalog versions:")
            for version, count in result:
                print(f"   {version}: {count} rows")
        else:
            print("📝 No catalog versions found in amis_catalog table")


def main():
    parser = argparse.ArgumentParser(description="Delete data from amis_catalog table")
    parser.add_argument("--db", required=True, help="Database URL")
    parser.add_argument("--action",
                       choices=["delete-all", "delete-version", "list-versions", "show-info"],
                       required=True,
                       help="Action to perform")
    parser.add_argument("--version", help="Catalog version to delete (required for delete-version)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")

    args = parser.parse_args()

    try:
        if args.action == "show-info":
            show_table_info(args.db)
        elif args.action == "list-versions":
            list_versions(args.db)
        elif args.action == "delete-all":
            delete_all_data(args.db, args.force)
        elif args.action == "delete-version":
            if not args.version:
                print("❌ --version is required for delete-version action")
                sys.exit(1)
            delete_version_data(args.db, args.version, args.force)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()