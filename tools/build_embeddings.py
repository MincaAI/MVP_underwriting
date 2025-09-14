#!/usr/bin/env python3
"""
Build embeddings for AMIS catalogue entries.

This script processes the amiscatalog table and generates embeddings for all entries
using the VehicleEmbedder. It can process entries in batches and update existing embeddings.
"""

import argparse
import logging
import sys
import pathlib
from typing import Optional, List, Dict, Any

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "ml" / "src"))

from sqlalchemy import text, update
from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.db.models import AmisCatalog
from app.ml.embed import get_embedder
from app.ml.retrieve import VehicleRetriever

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_vehicles_without_embeddings(session, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get vehicles that don't have embeddings yet."""
    query = """
    SELECT id, cvegs, brand, model, year, body, use, description, aliases
    FROM amiscatalog 
    WHERE embedding IS NULL
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    result = session.execute(text(query))
    
    vehicles = []
    for row in result.fetchall():
        vehicle = {
            "id": row[0],
            "cvegs": row[1], 
            "brand": row[2],
            "model": row[3],
            "year": row[4],
            "body": row[5],
            "use": row[6],
            "description": row[7],
            "aliases": row[8]
        }
        vehicles.append(vehicle)
    
    return vehicles

def update_embeddings(session, vehicle_embeddings: List[tuple]) -> None:
    """Update embeddings in the database."""
    try:
        # Prepare batch update
        update_data = []
        for vehicle_id, embedding in vehicle_embeddings:
            # Convert numpy array to list for JSON serialization
            embedding_list = embedding.tolist()
            # Convert to pgvector format string
            embedding_str = "[" + ",".join(map(str, embedding_list)) + "]"
            
            update_data.append({
                "id": vehicle_id,
                "embedding": embedding_str
            })
        
        # Batch update using SQLAlchemy
        if update_data:
            session.execute(
                text("""
                UPDATE amiscatalog 
                SET embedding = :embedding::vector 
                WHERE id = :id
                """),
                update_data
            )
            session.commit()
            logger.info(f"Updated {len(update_data)} embeddings in database")
    
    except Exception as e:
        logger.error(f"Failed to update embeddings: {e}")
        session.rollback()
        raise

def build_embeddings(batch_size: int = 32, 
                    limit: Optional[int] = None,
                    force_rebuild: bool = False,
                    create_index: bool = True) -> None:
    """
    Build embeddings for vehicles in the catalogue.
    
    Args:
        batch_size: Number of vehicles to process in each batch
        limit: Maximum number of vehicles to process (None for all)
        force_rebuild: If True, rebuild embeddings for all vehicles
        create_index: If True, create pgvector index after processing
    """
    # Initialize embedder
    logger.info("Initializing embedder...")
    embedder = get_embedder()
    
    # Create database session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get total count
        if force_rebuild:
            count_query = "SELECT COUNT(*) FROM amiscatalog"
        else:
            count_query = "SELECT COUNT(*) FROM amiscatalog WHERE embedding IS NULL"
        
        total_result = session.execute(text(count_query))
        total_count = total_result.fetchone()[0]
        
        if total_count == 0:
            logger.info("No vehicles need embedding processing")
            return
        
        logger.info(f"Processing {total_count} vehicles...")
        
        processed = 0
        while True:
            # Get batch of vehicles
            if force_rebuild:
                query = """
                SELECT id, cvegs, brand, model, year, body, use, description, aliases
                FROM amiscatalog 
                ORDER BY id
                LIMIT :limit OFFSET :offset
                """
                result = session.execute(text(query), {
                    "limit": batch_size,
                    "offset": processed
                })
            else:
                vehicles = get_vehicles_without_embeddings(session, batch_size)
                if not vehicles:
                    break
                
                # Convert to result format for consistency
                result = [(v["id"], v["cvegs"], v["brand"], v["model"], v["year"], 
                          v["body"], v["use"], v["description"], v["aliases"]) for v in vehicles]
            
            if force_rebuild:
                batch_data = result.fetchall()
                if not batch_data:
                    break
            else:
                batch_data = result
                if not batch_data:
                    break
            
            # Prepare vehicles for embedding
            vehicles_for_embedding = []
            vehicle_ids = []
            
            for row in batch_data:
                vehicle_id, cvegs, brand, model, year, body, use, description, aliases = row
                
                vehicles_for_embedding.append({
                    "brand": brand or "",
                    "model": model or "",
                    "year": year,
                    "description": description or "",
                    "body": body or "",
                    "use": use or ""
                })
                vehicle_ids.append(vehicle_id)
            
            # Generate embeddings
            logger.info(f"Generating embeddings for batch of {len(vehicles_for_embedding)} vehicles...")
            embeddings = embedder.embed_batch(vehicles_for_embedding, batch_size=batch_size)
            
            # Update database
            vehicle_embeddings = list(zip(vehicle_ids, embeddings))
            update_embeddings(session, vehicle_embeddings)
            
            processed += len(batch_data)
            logger.info(f"Processed {processed}/{total_count} vehicles ({processed/total_count*100:.1f}%)")
            
            if limit and processed >= limit:
                logger.info(f"Reached limit of {limit} vehicles")
                break
        
        logger.info(f"Completed processing {processed} vehicles")
        
        # Create vector index for efficient similarity search
        if create_index:
            logger.info("Creating pgvector index...")
            retriever = VehicleRetriever(engine, embedder)
            retriever.create_vector_index(session)
            logger.info("Vector index created successfully")
    
    except Exception as e:
        logger.error(f"Error during embedding generation: {e}")
        raise
    
    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description="Build embeddings for AMIS catalogue")
    parser.add_argument("--batch-size", type=int, default=32, 
                       help="Batch size for processing (default: 32)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Maximum number of vehicles to process")
    parser.add_argument("--force-rebuild", action="store_true",
                       help="Rebuild embeddings for all vehicles (not just missing ones)")
    parser.add_argument("--no-index", action="store_true",
                       help="Skip creating pgvector index")
    parser.add_argument("--model", type=str, default=None,
                       help="Sentence transformer model name to use")
    
    args = parser.parse_args()
    
    # Initialize embedder with custom model if specified
    if args.model:
        from app.ml.embed import VehicleEmbedder
        global _global_embedder
        _global_embedder = VehicleEmbedder(args.model)
    
    try:
        build_embeddings(
            batch_size=args.batch_size,
            limit=args.limit,
            force_rebuild=args.force_rebuild,
            create_index=not args.no_index
        )
        
        print("Embedding generation completed successfully!")
        
        # Print statistics
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            retriever = VehicleRetriever(engine)
            stats = retriever.get_statistics()
            
            print(f"\\nCatalogue Statistics:")
            print(f"  Total vehicles: {stats['total_vehicles']}")
            print(f"  With embeddings: {stats['vehicles_with_embeddings']}")
            print(f"  Coverage: {stats['vehicles_with_embeddings']/stats['total_vehicles']*100:.1f}%")
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Failed to build embeddings: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()