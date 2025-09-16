import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
import sys
import pathlib

# Add packages to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))

# AmisCatalog model removed - using raw SQL queries for amis_catalog table
from .embed import VehicleEmbedder, get_embedder

logger = logging.getLogger(__name__)

class VehicleRetriever:
    """
    Vehicle retrieval service using pgvector for similarity search.
    
    Provides semantic search over the AMIS vehicle catalogue using embeddings.
    """
    
    def __init__(self, engine: Engine, embedder: Optional[VehicleEmbedder] = None):
        """
        Initialize the retriever.
        
        Args:
            engine: SQLAlchemy engine for database connection
            embedder: VehicleEmbedder instance (uses global if None)
        """
        self.engine = engine
        self.embedder = embedder or get_embedder()
    
    def create_vector_index(self, session: Session) -> None:
        """
        Create pgvector index for efficient similarity search.
        
        Args:
            session: Database session
        """
        try:
            # Create HNSW index for cosine distance
            index_sql = """
            CREATE INDEX IF NOT EXISTS amis_catalog_embedding_cosine_idx
            ON amis_catalog USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
            session.execute(text(index_sql))
            session.commit()
            logger.info("Created pgvector HNSW index for cosine similarity")
            
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            session.rollback()
            raise
    
    def search_similar_vehicles(self,
                               query: str,
                               limit: int = 10,
                               min_similarity: float = 0.7,
                               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for vehicles similar to the query.
        
        Args:
            query: Search query (vehicle description, brand, model, etc.)
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            filters: Optional filters (brand, year_min, year_max, body, use)
            
        Returns:
            List of matching vehicles with similarity scores
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        return self.search_by_embedding(
            embedding=query_embedding,
            limit=limit,
            min_similarity=min_similarity,
            filters=filters
        )
    
    def search_by_embedding(self,
                           embedding: np.ndarray,
                           limit: int = 10,
                           min_similarity: float = 0.7,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search using a pre-computed embedding vector.
        
        Args:
            embedding: Query embedding vector
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            filters: Optional filters (brand, year_min, year_max, body, use)
            
        Returns:
            List of matching vehicles with similarity scores
        """
        with self.engine.begin() as conn:
            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            
            # Build base query with similarity search
            sql_parts = [
                "SELECT *,",
                f"1 - (embedding <=> '{embedding_str}'::vector) as similarity",
                "FROM amis_catalog",
                "WHERE embedding IS NOT NULL"
            ]
            
            # Add filters
            params = {}
            if filters:
                if filters.get("brand"):
                    sql_parts.append("AND brand = :brand")
                    params["brand"] = filters["brand"]
                
                if filters.get("year_min"):
                    sql_parts.append("AND year >= :year_min")
                    params["year_min"] = filters["year_min"]
                
                if filters.get("year_max"):
                    sql_parts.append("AND year <= :year_max")
                    params["year_max"] = filters["year_max"]
                
                if filters.get("body"):
                    sql_parts.append("AND body = :body")
                    params["body"] = filters["body"]
                
                if filters.get("use"):
                    sql_parts.append("AND use = :use_type")
                    params["use_type"] = filters["use"]
            
            # Add similarity threshold and ordering
            sql_parts.extend([
                f"AND (1 - (embedding <=> '{embedding_str}'::vector)) >= :min_similarity",
                "ORDER BY embedding <=> :embedding",
                "LIMIT :limit"
            ])
            
            params.update({
                "min_similarity": min_similarity,
                "embedding": embedding_str,
                "limit": limit
            })
            
            sql = " ".join(sql_parts)
            
            result = conn.execute(text(sql), params)
            rows = result.fetchall()
            
            # Convert to list of dictionaries
            vehicles = []
            for row in rows:
                vehicle_dict = dict(row._mapping)
                
                # Parse aliases JSON if present
                if vehicle_dict.get("aliases"):
                    import json
                    try:
                        vehicle_dict["aliases"] = json.loads(vehicle_dict["aliases"])
                    except (json.JSONDecodeError, TypeError):
                        vehicle_dict["aliases"] = {}
                
                vehicles.append(vehicle_dict)
            
            logger.info(f"Found {len(vehicles)} similar vehicles for query (similarity >= {min_similarity})")
            return vehicles
    
    def find_exact_matches(self,
                          brand: str,
                          model: str,
                          year: Optional[int] = None,
                          body: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find exact matches for vehicle specifications.
        
        Args:
            brand: Vehicle brand (normalized)
            model: Vehicle model (normalized)
            year: Manufacturing year
            body: Body type
            
        Returns:
            List of exact matching vehicles
        """
        with self.engine.begin() as conn:
            # Build query for exact matches
            sql_parts = ["SELECT * FROM amis_catalog WHERE brand = :brand AND model = :model"]
            params = {"brand": brand.lower().strip(), "model": model.lower().strip()}
            
            if year:
                sql_parts.append("AND year = :year")
                params["year"] = year
            
            if body:
                sql_parts.append("AND body = :body")
                params["body"] = body.lower().strip()
            
            sql = " ".join(sql_parts)
            
            result = conn.execute(text(sql), params)
            rows = result.fetchall()
            
            # Convert to list of dictionaries
            vehicles = []
            for row in rows:
                vehicle_dict = dict(row._mapping)
                
                # Parse aliases JSON if present
                if vehicle_dict.get("aliases"):
                    import json
                    try:
                        vehicle_dict["aliases"] = json.loads(vehicle_dict["aliases"])
                    except (json.JSONDecodeError, TypeError):
                        vehicle_dict["aliases"] = {}
                
                vehicles.append(vehicle_dict)
            
            return vehicles
    
    def search_with_fallback(self,
                            query: str,
                            brand: Optional[str] = None,
                            model: Optional[str] = None,
                            year: Optional[int] = None,
                            body: Optional[str] = None,
                            limit: int = 10) -> Tuple[List[Dict[str, Any]], str]:
        """
        Search with multiple strategies (exact match -> similarity search).
        
        Args:
            query: Search query
            brand: Known brand (optional)
            model: Known model (optional)  
            year: Known year (optional)
            body: Known body type (optional)
            limit: Maximum results
            
        Returns:
            Tuple of (results, search_strategy_used)
        """
        # Try exact match first if we have brand and model
        if brand and model:
            exact_matches = self.find_exact_matches(brand, model, year, body)
            if exact_matches:
                return exact_matches[:limit], "exact_match"
        
        # Try high similarity search
        filters = {}
        if brand:
            filters["brand"] = brand.lower().strip()
        if year:
            filters["year_min"] = year
            filters["year_max"] = year
        if body:
            filters["body"] = body.lower().strip()
        
        # High similarity threshold first
        high_sim_results = self.search_similar_vehicles(
            query=query,
            limit=limit,
            min_similarity=0.85,
            filters=filters
        )
        
        if high_sim_results:
            return high_sim_results, "high_similarity"
        
        # Medium similarity threshold
        med_sim_results = self.search_similar_vehicles(
            query=query,
            limit=limit,
            min_similarity=0.7,
            filters=filters
        )
        
        if med_sim_results:
            return med_sim_results, "medium_similarity"
        
        # Low similarity threshold (last resort)
        low_sim_results = self.search_similar_vehicles(
            query=query,
            limit=limit,
            min_similarity=0.5,
            filters=filters
        )
        
        return low_sim_results, "low_similarity" if low_sim_results else "no_match"
    
    def get_vehicle_by_cvegs(self, cvegs: str) -> Optional[Dict[str, Any]]:
        """
        Get vehicle by CVEGS code.
        
        Args:
            cvegs: CVEGS vehicle code
            
        Returns:
            Vehicle dictionary or None if not found
        """
        with self.engine.begin() as conn:
            result = conn.execute(
                text("SELECT * FROM amis_catalog WHERE cvegs = :cvegs"),
                {"cvegs": cvegs}
            )
            row = result.fetchone()
            
            if row:
                vehicle_dict = dict(row._mapping)
                
                # Parse aliases JSON if present
                if vehicle_dict.get("aliases"):
                    import json
                    try:
                        vehicle_dict["aliases"] = json.loads(vehicle_dict["aliases"])
                    except (json.JSONDecodeError, TypeError):
                        vehicle_dict["aliases"] = {}
                
                return vehicle_dict
            
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the vehicle catalogue.
        
        Returns:
            Dictionary with catalogue statistics
        """
        with self.engine.begin() as conn:
            stats = {}
            
            # Total vehicles
            result = conn.execute(text("SELECT COUNT(*) as total FROM amis_catalog"))
            stats["total_vehicles"] = result.fetchone()[0]
            
            # Vehicles with embeddings
            result = conn.execute(text("SELECT COUNT(*) as with_embeddings FROM amis_catalog WHERE embedding IS NOT NULL"))
            stats["vehicles_with_embeddings"] = result.fetchone()[0]
            
            # Brand distribution
            result = conn.execute(text("""
                SELECT brand, COUNT(*) as count 
                FROM amis_catalog 
                WHERE brand IS NOT NULL 
                GROUP BY brand 
                ORDER BY count DESC 
                LIMIT 10
            """))
            stats["top_brands"] = [{"brand": row[0], "count": row[1]} for row in result.fetchall()]
            
            # Year distribution
            result = conn.execute(text("""
                SELECT year, COUNT(*) as count 
                FROM amis_catalog 
                WHERE year IS NOT NULL 
                GROUP BY year 
                ORDER BY year DESC 
                LIMIT 10
            """))
            stats["recent_years"] = [{"year": row[0], "count": row[1]} for row in result.fetchall()]
            
            return stats