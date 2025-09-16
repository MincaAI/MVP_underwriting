#!/usr/bin/env python3
import argparse
import csv
import sys
from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.db.session import engine as _engine


def quote_ident(name: str) -> str:
    # Double-quote identifier and escape embedded quotes by doubling them
    return '"' + name.replace('"', '""') + '"'


def ensure_table(engine: Engine, table_name: str, columns: List[str], drop_and_create: bool = True) -> None:
    cols_sql = ", ".join(f"{quote_ident(c)} TEXT" for c in columns)
    with engine.begin() as cx:
        if drop_and_create:
            cx.execute(text(f'DROP TABLE IF EXISTS {quote_ident(table_name)} CASCADE'))
            cx.execute(text(f'CREATE TABLE {quote_ident(table_name)} ({cols_sql})'))
        else:
            # Fallback: try to create if not exists (best-effort)
            cx.execute(text(f'CREATE TABLE IF NOT EXISTS {quote_ident(table_name)} ({cols_sql})'))

        # Optional helpful indexes if these columns exist
        for idx_col in ["AMIS", "Marca", "Submarca", "Año modelo"]:
            if idx_col in columns:
                cx.execute(text(
                    f'CREATE INDEX IF NOT EXISTS {quote_ident("ix_" + table_name + "_" + idx_col)} '
                    f'ON {quote_ident(table_name)} ({quote_ident(idx_col)})'
                ))


def truncate_table(engine: Engine, table_name: str) -> None:
    with engine.begin() as cx:
        cx.execute(text(f'TRUNCATE TABLE {quote_ident(table_name)}'))


def load_csv_rows(csv_path: str) -> (List[str], List[List[str]]):
    # Read as raw strings, do not interpret numbers/dates
    # Use utf-8-sig to gracefully handle BOM if present
    with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise RuntimeError("CSV file appears to be empty.")
        rows = [row for row in reader]
    return header, rows


def bulk_insert(engine: Engine, table_name: str, columns: List[str], rows: List[List[str]], batch_size: int = 1000) -> int:
    if not rows:
        return 0

    cols_sql = ", ".join(quote_ident(c) for c in columns)
    # Named parameters p0, p1, ...
    param_names = [f"p{i}" for i in range(len(columns))]
    params_sql = ", ".join(f":{p}" for p in param_names)
    insert_sql = text(f'INSERT INTO {quote_ident(table_name)} ({cols_sql}) VALUES ({params_sql})')

    total = 0
    with engine.begin() as cx:
        batch = []
        for row in rows:
            # Pad or trim row to match columns length to avoid errors
            values = (row + [""] * len(columns))[:len(columns)]
            payload = {param_names[i]: values[i] for i in range(len(columns))}
            batch.append(payload)
            if len(batch) >= batch_size:
                cx.execute(insert_sql, batch)
                total += len(batch)
                batch = []
        if batch:
            cx.execute(insert_sql, batch)
            total += len(batch)
    return total


def main():
    ap = argparse.ArgumentParser(description="Load AMIS CSV into a raw table with identical columns/values (no transformation).")
    ap.add_argument("--file", required=True, help="Path to AMIS CSV (UTF-8/UTF-8-SIG)")
    ap.add_argument("--table", default="amis_raw", help="Destination table name (default: amis_raw)")
    ap.add_argument("--no-drop-create", action="store_true", help="Do not drop/recreate table; attempt create if not exists")
    ap.add_argument("--no-truncate", action="store_true", help="Do not truncate before insert")
    ap.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts (default: 1000)")
    args = ap.parse_args()

    csv_path = args.file
    table_name = args.table
    drop_create = not args.no_drop_create
    do_truncate = not args.no_truncate

    try:
        header, rows = load_csv_rows(csv_path)
    except Exception as e:
        print(f"Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure header columns are unique
    if len(set(header)) != len(header):
        print("CSV header contains duplicate column names, which cannot be mapped 1:1 into a table.", file=sys.stderr)
        sys.exit(1)

    # Create/ensure table with exact header names as TEXT
    try:
        ensure_table(_engine, table_name, header, drop_and_create=drop_create)
    except Exception as e:
        print(f"Failed to ensure destination table: {e}", file=sys.stderr)
        sys.exit(1)

    # Optionally truncate
    if do_truncate:
        try:
            truncate_table(_engine, table_name)
        except Exception as e:
            print(f"Failed to truncate destination table: {e}", file=sys.stderr)
            sys.exit(1)

    # Insert rows in batches
    try:
        inserted = bulk_insert(_engine, table_name, header, rows, batch_size=args.batch_size)
    except Exception as e:
        print(f"Failed to insert rows: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {inserted} rows into {table_name} with columns: {header}")


if __name__ == "__main__":
    main()
