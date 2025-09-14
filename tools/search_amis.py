#!/usr/bin/env python3
"""
Search AMIS catalogue using semantic similarity.

This script provides a command-line interface for searching the AMIS vehicle catalogue
using natural language queries and semantic similarity search.
"""

import argparse
import json
import sys
import pathlib
from typing import Optional, Dict, Any

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "ml" / "src"))

from app.db.session import engine
from app.ml.retrieve import VehicleRetriever
from app.ml.embed import get_embedder

def format_vehicle_result(vehicle: Dict[str, Any], show_embedding: bool = False) -> str:
    """Format a vehicle result for display."""
    lines = []
    
    # Header with CVEGS and basic info
    lines.append(f"CVEGS: {vehicle.get('cvegs', 'N/A')}")
    lines.append(f"Vehicle: {vehicle.get('brand', '')} {vehicle.get('model', '')} {vehicle.get('year', '')}")
    
    # Additional details
    if vehicle.get('body'):
        lines.append(f"Body: {vehicle['body']}")
    if vehicle.get('use'):
        lines.append(f"Use: {vehicle['use']}")
    if vehicle.get('description'):
        lines.append(f"Description: {vehicle['description']}")
    
    # Similarity score if available
    if 'similarity' in vehicle:
        lines.append(f"Similarity: {vehicle['similarity']:.3f}")
    
    # Aliases if available
    if vehicle.get('aliases'):
        aliases = vehicle['aliases']
        alias_parts = []
        for alias_type, alias_list in aliases.items():
            if alias_list:
                alias_parts.append(f"{alias_type}: {', '.join(alias_list)}")
        if alias_parts:
            lines.append(f"Aliases: {'; '.join(alias_parts)}")
    
    # Embedding vector if requested (truncated)
    if show_embedding and vehicle.get('embedding'):
        emb_str = str(vehicle['embedding'])[:100] + "..." if len(str(vehicle['embedding'])) > 100 else str(vehicle['embedding'])
        lines.append(f"Embedding: {emb_str}")
    
    return "\\n".join(lines)

def search_vehicles(query: str,
                   limit: int = 10,
                   min_similarity: float = 0.7,
                   brand: Optional[str] = None,
                   year_min: Optional[int] = None,
                   year_max: Optional[int] = None,
                   body: Optional[str] = None,
                   use: Optional[str] = None,
                   output_format: str = "text") -> None:
    """Search for vehicles and display results."""
    
    # Initialize retriever
    embedder = get_embedder()
    retriever = VehicleRetriever(engine, embedder)
    
    # Build filters
    filters = {}
    if brand:
        filters["brand"] = brand.lower().strip()
    if year_min:
        filters["year_min"] = year_min
    if year_max:
        filters["year_max"] = year_max
    if body:
        filters["body"] = body.lower().strip()
    if use:
        filters["use"] = use.lower().strip()
    
    # Perform search
    print(f"Searching for: '{query}'")
    if filters:
        print(f"Filters: {filters}")
    print(f"Minimum similarity: {min_similarity}")
    print("-" * 50)
    
    try:
        results = retriever.search_similar_vehicles(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            filters=filters
        )
        
        if not results:
            print("No matching vehicles found.")
            return
        
        print(f"Found {len(results)} matching vehicles:")
        print()
        
        if output_format == "json":
            # JSON output
            print(json.dumps(results, indent=2, default=str))
        else:
            # Text output
            for i, vehicle in enumerate(results, 1):
                print(f"=== Result {i} ===")
                print(format_vehicle_result(vehicle))
                print()
    
    except Exception as e:
        print(f"Error during search: {e}")
        sys.exit(1)

def search_with_fallback(query: str,
                        brand: Optional[str] = None,
                        model: Optional[str] = None,
                        year: Optional[int] = None,
                        body: Optional[str] = None,
                        limit: int = 10,
                        output_format: str = "text") -> None:
    """Search using fallback strategy."""
    
    # Initialize retriever
    embedder = get_embedder()
    retriever = VehicleRetriever(engine, embedder)
    
    print(f"Searching with fallback strategy for: '{query}'")
    if brand or model or year or body:
        print(f"Known attributes - Brand: {brand}, Model: {model}, Year: {year}, Body: {body}")
    print("-" * 50)
    
    try:
        results, strategy = retriever.search_with_fallback(
            query=query,
            brand=brand,
            model=model,
            year=year,
            body=body,
            limit=limit
        )
        
        print(f"Search strategy used: {strategy}")
        print()
        
        if not results:
            print("No matching vehicles found with any strategy.")
            return
        
        print(f"Found {len(results)} matching vehicles:")
        print()
        
        if output_format == "json":
            # JSON output
            output_data = {
                "strategy": strategy,
                "results": results
            }
            print(json.dumps(output_data, indent=2, default=str))
        else:
            # Text output
            for i, vehicle in enumerate(results, 1):
                print(f"=== Result {i} ===")
                print(format_vehicle_result(vehicle))
                print()
    
    except Exception as e:
        print(f"Error during search: {e}")
        sys.exit(1)

def get_vehicle_by_cvegs(cvegs: str, output_format: str = "text") -> None:
    """Get vehicle by CVEGS code."""
    
    # Initialize retriever
    embedder = get_embedder()
    retriever = VehicleRetriever(engine, embedder)
    
    try:
        vehicle = retriever.get_vehicle_by_cvegs(cvegs)
        
        if not vehicle:
            print(f"No vehicle found with CVEGS: {cvegs}")
            return
        
        if output_format == "json":
            print(json.dumps(vehicle, indent=2, default=str))
        else:
            print(f"Vehicle found for CVEGS: {cvegs}")
            print("-" * 30)
            print(format_vehicle_result(vehicle))
    
    except Exception as e:
        print(f"Error retrieving vehicle: {e}")
        sys.exit(1)

def show_statistics() -> None:
    """Show catalogue statistics."""
    
    # Initialize retriever
    embedder = get_embedder()
    retriever = VehicleRetriever(engine, embedder)
    
    try:
        stats = retriever.get_statistics()
        
        print("AMIS Catalogue Statistics")
        print("=" * 30)
        print(f"Total vehicles: {stats['total_vehicles']}")
        print(f"With embeddings: {stats['vehicles_with_embeddings']}")
        print(f"Coverage: {stats['vehicles_with_embeddings']/stats['total_vehicles']*100:.1f}%")
        print()
        
        print("Top Brands:")
        for brand_info in stats['top_brands']:
            print(f"  {brand_info['brand']}: {brand_info['count']} vehicles")
        print()
        
        print("Recent Years:")
        for year_info in stats['recent_years']:
            print(f"  {year_info['year']}: {year_info['count']} vehicles")
    
    except Exception as e:
        print(f"Error retrieving statistics: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Search AMIS vehicle catalogue")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search vehicles by query")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    search_parser.add_argument("--min-similarity", type=float, default=0.7, 
                             help="Minimum similarity threshold (0-1)")
    search_parser.add_argument("--brand", help="Filter by brand")
    search_parser.add_argument("--year-min", type=int, help="Minimum year")
    search_parser.add_argument("--year-max", type=int, help="Maximum year")
    search_parser.add_argument("--body", help="Filter by body type")
    search_parser.add_argument("--use", help="Filter by use type")
    search_parser.add_argument("--format", choices=["text", "json"], default="text",
                             help="Output format")
    
    # Fallback search command
    fallback_parser = subparsers.add_parser("fallback", help="Search with fallback strategy")
    fallback_parser.add_argument("query", help="Search query")
    fallback_parser.add_argument("--brand", help="Known brand")
    fallback_parser.add_argument("--model", help="Known model")
    fallback_parser.add_argument("--year", type=int, help="Known year")
    fallback_parser.add_argument("--body", help="Known body type")
    fallback_parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    fallback_parser.add_argument("--format", choices=["text", "json"], default="text",
                               help="Output format")
    
    # Get by CVEGS command
    cvegs_parser = subparsers.add_parser("get", help="Get vehicle by CVEGS code")
    cvegs_parser.add_argument("cvegs", help="CVEGS code")
    cvegs_parser.add_argument("--format", choices=["text", "json"], default="text",
                            help="Output format")
    
    # Statistics command
    subparsers.add_parser("stats", help="Show catalogue statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "search":
        search_vehicles(
            query=args.query,
            limit=args.limit,
            min_similarity=args.min_similarity,
            brand=args.brand,
            year_min=args.year_min,
            year_max=args.year_max,
            body=args.body,
            use=args.use,
            output_format=args.format
        )
    
    elif args.command == "fallback":
        search_with_fallback(
            query=args.query,
            brand=args.brand,
            model=args.model,
            year=args.year,
            body=args.body,
            limit=args.limit,
            output_format=args.format
        )
    
    elif args.command == "get":
        get_vehicle_by_cvegs(args.cvegs, args.format)
    
    elif args.command == "stats":
        show_statistics()

if __name__ == "__main__":
    main()