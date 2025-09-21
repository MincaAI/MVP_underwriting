#!/usr/bin/env python3
"""
Extract brand data from AMIS catalog to create brand lookup table.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
from sqlalchemy import create_engine, text
from vehicle_codifier.config import get_settings

def extract_brand_data():
    """Extract comprehensive brand data from AMIS catalog."""
    settings = get_settings()
    engine = create_engine(settings.database_url)

    print("🔍 Extracting brand data from AMIS catalog...")

    # Query to get all brands with metadata
    query = text("""
        SELECT
            marca as brand_name,
            COUNT(*) as vehicle_count,
            MIN(modelo) as earliest_year,
            MAX(modelo) as latest_year,
            ARRAY_AGG(DISTINCT tipveh) as vehicle_types,
            ARRAY_AGG(DISTINCT cvesegm) as segments
        FROM amis_catalog
        WHERE marca IS NOT NULL
        AND catalog_version = (
            SELECT version
            FROM catalog_import
            WHERE status IN ('ACTIVE', 'LOADED')
            ORDER BY version DESC
            LIMIT 1
        )
        GROUP BY marca
        ORDER BY vehicle_count DESC;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        brands = []

        for row in result:
            brand_data = {
                "brand_name": row.brand_name,
                "vehicle_count": row.vehicle_count,
                "earliest_year": row.earliest_year,
                "latest_year": row.latest_year,
                "vehicle_types": row.vehicle_types,
                "segments": row.segments
            }
            brands.append(brand_data)

    print(f"✅ Extracted {len(brands)} unique brands")

    # Show top brands
    print("\n🏆 Top 20 Brands by Vehicle Count:")
    for i, brand in enumerate(brands[:20]):
        types = ", ".join(brand["vehicle_types"][:3])  # Show first 3 types
        print(f"   {i+1:2d}. {brand['brand_name']:<15} ({brand['vehicle_count']:>4,} vehicles, {types})")

    # Save to JSON file
    output_file = "brand_lookup_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(brands, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Brand data saved to: {output_file}")

    # Create brand aliases mapping
    brand_aliases = create_brand_aliases(brands)

    aliases_file = "brand_aliases.json"
    with open(aliases_file, 'w', encoding='utf-8') as f:
        json.dump(brand_aliases, f, indent=2, ensure_ascii=False)

    print(f"💾 Brand aliases saved to: {aliases_file}")

    return brands, brand_aliases

def create_brand_aliases(brands):
    """Create brand aliases and variations mapping."""
    aliases = {}

    # Extract all brand names
    brand_names = [brand["brand_name"] for brand in brands]

    # Manual aliases for common variations (all uppercase now)
    manual_aliases = {
        # Commercial truck brands
        "freightliner": "freightliner",
        "international": "international",
        "kenworth": "kenworth",
        "peterbilt": "peterbilt",
        "mack": "mack",
        "volvo": "volvo",
        "man": "man",

        # Passenger car brands
        "bmw": "bmw",
        "mercedes-benz": "mercedes-benz",
        "mercedes benz": "mercedes-benz",
        "mercedes": "mercedes-benz",
        "vw": "volkswagen",
        "volkswagen": "volkswagen",
        "chevy": "chevrolet",
        "chevrolet": "chevrolet",

        # Other common variations
        "ford": "ford",
        "toyota": "toyota",
        "honda": "honda",
        "nissan": "nissan",
        "hyundai": "hyundai",
        "kia": "kia",
        "mazda": "mazda",
        "subaru": "subaru",
        "mitsubishi": "mitsubishi"
    }

    # Add manual aliases
    for alias, brand in manual_aliases.items():
        # Check if uppercase version exists in brand_names, and store uppercase
        if brand.upper() in brand_names:
            aliases[alias.upper()] = brand.upper()

    # Add exact matches (uppercase -> uppercase)
    for brand in brand_names:
        aliases[brand.upper()] = brand.upper()

        # Add common variations
        if " " in brand:
            # "LAND ROVER" -> "LAND ROVER", "LANDROVER"
            aliases[brand.upper().replace(" ", "")] = brand.upper()
            aliases[brand.upper().replace(" ", "_")] = brand.upper()

        if "-" in brand:
            # "MERCEDES-BENZ" -> "MERCEDES-BENZ", "MERCEDESBENZ"
            aliases[brand.upper().replace("-", "")] = brand.upper()
            aliases[brand.upper().replace("-", "_")] = brand.upper()

    print(f"\n🔤 Created {len(aliases)} brand aliases")

    # Show sample aliases
    print("\n📋 Sample Brand Aliases:")
    sample_aliases = list(aliases.items())[:15]
    for alias, brand in sample_aliases:
        print(f"   '{alias}' -> '{brand}'")

    return aliases

if __name__ == "__main__":
    try:
        brands, aliases = extract_brand_data()
        print(f"\n🎉 Brand extraction completed successfully!")
        print(f"   - {len(brands)} unique brands")
        print(f"   - {len(aliases)} brand aliases")
        print(f"   - Files: brand_lookup_data.json, brand_aliases.json")

    except Exception as e:
        print(f"❌ Error extracting brand data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)