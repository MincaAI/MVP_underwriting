#!/usr/bin/env python3
"""
Load any Excel file into a raw table that mirrors all columns 1:1 as TEXT.
"""

import argparse
import pathlib
import sys
from typing import List

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add DB package to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "db" / "src"))
from app.db.session import engine as _engine  # noqa: E402


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def ensure_table(engine: Engine, table_name: str, columns: List[str], drop_and_create: bool = True) -> None:
    cols_sql = ", ".join(f"{quote_ident(c)} TEXT" for c in columns)
    with engine.begin() as cx:
        if drop_and_create:
            cx.execute(text(f'DROP TABLE IF EXISTS {quote_ident(table_name)} CASCADE'))
            cx.execute(text(f'CREATE TABLE {quote_ident(table_name)} ({cols_sql})'))
        else:
            cx.execute(text(f'CREATE TABLE IF NOT EXISTS {quote_ident(table_name)} ({cols_sql})'))


def bulk_insert(engine: Engine, table_name: str, columns: List[str], rows: List[List[str]], batch_size: int = 1000) -> int:
    if not rows:
        return 0
    cols_sql = ", ".join(quote_ident(c) for c in columns)
    param_names = [f"p{i}" for i in range(len(columns))]
    params_sql = ", ".join(f":{p}" for p in param_names)
    insert_sql = text(f'INSERT INTO {quote_ident(table_name)} ({cols_sql}) VALUES ({params_sql})')

    total = 0
    with engine.begin() as cx:
        batch = []
        for r in rows:
            values = (r + [""] * len(columns))[:len(columns)]
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
    ap = argparse.ArgumentParser(description="Load Excel into a raw table with identical columns/values (TEXT).")
    ap.add_argument("--file", required=True, help="Path to Excel file (.xlsx)")
    ap.add_argument("--sheet", default=None, help="Sheet name (default: first sheet)")
    ap.add_argument("--table", default=None, help="Destination table name (default: <filename>_raw)")
    ap.add_argument("--no-drop-create", action="store_true", help="Do not drop/recreate table; attempt create if not exists")
    ap.add_argument("--batch-size", type=int, default=1000, help="Batch size (default: 1000)")
    args = ap.parse_args()

    xlsx_path = pathlib.Path(args.file)
    if not xlsx_path.exists():
        print(f"File not found: {xlsx_path}", file=sys.stderr)
        sys.exit(1)

    table_name = args.table or (xlsx_path.stem.lower().replace("-", "_").replace(" ", "_") + "_raw")
    drop_create = not args.no_drop_create

    # Read everything as string, keep blanks as ""
    try:
        xl = pd.ExcelFile(xlsx_path)
        sheet_name = args.sheet or xl.sheet_names[0]
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name, dtype=str).fillna("")
    except Exception as e:
        print(f"Failed to read Excel: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure unique column names
    cols = list(map(str, df.columns))
    seen = {}
    uniq_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 1
            uniq_cols.append(c)
        else:
            seen[c] += 1
            uniq_cols.append(f"{c}_{seen[c]}")
    if uniq_cols != cols:
        df.columns = uniq_cols
        cols = uniq_cols

    try:
        ensure_table(_engine, table_name, cols, drop_and_create=drop_create)
    except Exception as e:
        print(f"Failed to ensure destination table: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert rows to list of lists
    rows = df.astype(str).values.tolist()

    try:
        inserted = bulk_insert(_engine, table_name, cols, rows, batch_size=args.batch_size)
    except Exception as e:
        print(f"Failed to insert rows: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {inserted} rows into {table_name} with columns: {cols}")


if __name__ == "__main__":
    main()


