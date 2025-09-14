#!/usr/bin/env python3
import argparse, pathlib, sys, json
import pandas as pd
from sqlalchemy import insert
from app.db.session import engine
from app.db.models import AmisCatalog

def read_alias_yaml(path: pathlib.Path):
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Alias load warning {path}: {e}", file=sys.stderr); return {}

def norm(s):
    import re, unicodedata
    if s is None: return None
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s)
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="AMIS/CVEGS csv/xlsx")
    ap.add_argument("--sheet", default=None, help="Sheet name for xlsx")
    ap.add_argument("--brands", default="configs/aliases/brands.yaml")
    ap.add_argument("--models", default="configs/aliases/models.yaml")
    ap.add_argument("--bodies", default="configs/aliases/bodies.yaml")
    args = ap.parse_args()

    p = pathlib.Path(args.file)
    if p.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(p, sheet_name=args.sheet)
    else:
        df = pd.read_csv(p)

    # Try common headings (adjust here if names differ)
    cols = {c.lower().strip(): c for c in df.columns}
    def col(*names):
        for n in names:
            if n in cols: return cols[n]
        raise KeyError(f"Missing column: {names}")

    cve = col("cvegs","cveg","clave","clave vehiculo","clave vehículo")
    brand = col("marca","brand")
    model = col("submarca","modelo","model")
    year = col("año","anio","year")
    body = cols.get("carroceria") or cols.get("carrocería") or cols.get("body")
    use  = cols.get("uso") or cols.get("use")
    desc = cols.get("descripcion") or cols.get("descripción") or cols.get("description")

    brand_aliases = read_alias_yaml(pathlib.Path(args.brands))
    model_aliases = read_alias_yaml(pathlib.Path(args.models))
    body_aliases  = read_alias_yaml(pathlib.Path(args.bodies))

    rows = []
    for _, r in df.iterrows():
        rows.append({
            "cvegs": str(r[cve]).strip(),
            "brand": norm(r[brand]),
            "model": norm(r[model]),
            "year": int(r[year]) if pd.notnull(r[year]) else None,
            "body": norm(r[body]) if body else None,
            "use":  norm(r[use]) if use else None,
            "description": str(r[desc]).strip() if desc and pd.notnull(r[desc]) else None,
            "aliases": {
                "brand": brand_aliases.get(norm(r[brand]), []),
                "model": model_aliases.get(norm(r[model]), []),
                "body":  body_aliases.get(norm(r[body])) if body else [],
            },
            "embedding": None,  # will be filled in step 5
        })

    with engine.begin() as cx:
        # optional: clean table first if desired
        cx.execute(AmisCatalog.__table__.delete())
        cx.execute(insert(AmisCatalog), rows)

    print(f"Loaded {len(rows)} rows into amiscatalog.")

if __name__ == "__main__":
    main()