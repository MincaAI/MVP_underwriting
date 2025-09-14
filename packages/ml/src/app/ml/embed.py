import logging
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from .normalize import normalize_text, extract_vehicle_features

logger = logging.getLogger(__name__)

class VehicleEmbedder:
    """
    Vehicle description embedding service using multilingual sentence transformers.
    
    Optimized for Spanish and English vehicle descriptions with feature extraction.
    """
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize the embedder with a multilingual model.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.dimension = 384  # Default for MiniLM-L12-v2
        
    def _ensure_model_loaded(self):
        """Lazy load the sentence transformer model."""
        if self.model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Embedding dimension: {self.dimension}")
    
    def prepare_text_for_embedding(self, 
                                 brand: str,
                                 model: str, 
                                 year: Optional[int] = None,
                                 description: Optional[str] = None,
                                 body: Optional[str] = None,
                                 use: Optional[str] = None) -> str:
        """
        Prepare a structured text representation for embedding.
        
        Args:
            brand: Vehicle brand/manufacturer
            model: Vehicle model name
            year: Manufacturing year
            description: Detailed description
            body: Body type
            use: Intended use
            
        Returns:
            Formatted text ready for embedding
        """
        # Normalize all inputs
        brand = normalize_text(brand) if brand else ""
        model = normalize_text(model) if model else ""
        body = normalize_text(body) if body else ""
        use = normalize_text(use) if use else ""
        description = normalize_text(description) if description else ""
        
        # Build structured representation
        parts = []
        
        # Core vehicle identification
        if brand and model:
            if year:
                parts.append(f"{brand} {model} {year}")
            else:
                parts.append(f"{brand} {model}")
        elif brand:
            parts.append(brand)
        elif model:
            parts.append(model)
            
        # Add body type and use
        if body:
            parts.append(f"tipo {body}")
        if use:
            parts.append(f"uso {use}")
            
        # Add detailed description with feature extraction
        if description:
            # Extract structured features
            features = extract_vehicle_features(description)
            
            # Add original description
            parts.append(description)
            
            # Add extracted features as structured text
            feature_parts = []
            for feature_type, feature_list in features.items():
                if feature_list:
                    feature_parts.append(" ".join(feature_list))
            
            if feature_parts:
                parts.append(" ".join(feature_parts))
        
        return " ".join(parts).strip()
    
    def embed_vehicle(self,
                     brand: str,
                     model: str,
                     year: Optional[int] = None, 
                     description: Optional[str] = None,
                     body: Optional[str] = None,
                     use: Optional[str] = None) -> np.ndarray:
        """
        Generate embedding for a single vehicle.
        
        Args:
            brand: Vehicle brand/manufacturer
            model: Vehicle model name  
            year: Manufacturing year
            description: Detailed description
            body: Body type
            use: Intended use
            
        Returns:
            Embedding vector as numpy array
        """
        self._ensure_model_loaded()
        
        text = self.prepare_text_for_embedding(brand, model, year, description, body, use)
        
        if not text.strip():
            logger.warning("Empty text for embedding, returning zero vector")
            return np.zeros(self.dimension, dtype=np.float32)
        
        # Generate embedding
        with torch.no_grad():
            embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        
        return embedding.astype(np.float32)
    
    def embed_batch(self, vehicles: List[Dict[str, Any]], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for multiple vehicles efficiently.
        
        Args:
            vehicles: List of vehicle dictionaries with keys: brand, model, year, description, body, use
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        self._ensure_model_loaded()
        
        if not vehicles:
            return []
        
        # Prepare all texts
        texts = []
        for vehicle in vehicles:
            text = self.prepare_text_for_embedding(
                brand=vehicle.get("brand", ""),
                model=vehicle.get("model", ""),
                year=vehicle.get("year"),
                description=vehicle.get("description"),
                body=vehicle.get("body"),
                use=vehicle.get("use")
            )
            texts.append(text if text.strip() else " ")  # Avoid empty strings
        
        # Generate embeddings in batches
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            with torch.no_grad():
                batch_embeddings = self.model.encode(
                    batch_texts,
                    batch_size=len(batch_texts),
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=len(texts) > 100
                )
            
            embeddings.extend([emb.astype(np.float32) for emb in batch_embeddings])
            
            if len(texts) > 100:
                logger.info(f"Processed {min(i + batch_size, len(texts))}/{len(texts)} embeddings")
        
        return embeddings
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding vector
        """
        self._ensure_model_loaded()
        
        # Normalize the query
        normalized_query = normalize_text(query)
        
        if not normalized_query.strip():
            logger.warning("Empty query for embedding, returning zero vector")
            return np.zeros(self.dimension, dtype=np.float32)
        
        # Generate embedding
        with torch.no_grad():
            embedding = self.model.encode(normalized_query, convert_to_numpy=True, normalize_embeddings=True)
        
        return embedding.astype(np.float32)
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Normalize vectors (should already be normalized from sentence-transformers)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Ensure result is in [0, 1] range
        return max(0.0, min(1.0, float(similarity)))
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        self._ensure_model_loaded()
        return self.dimension

# Global embedder instance for reuse
_global_embedder: Optional[VehicleEmbedder] = None

def get_embedder(model_name: Optional[str] = None) -> VehicleEmbedder:
    """
    Get a global embedder instance for reuse across the application.
    
    Args:
        model_name: Optional model name, uses default if not specified
        
    Returns:
        VehicleEmbedder instance
    """
    global _global_embedder
    
    if _global_embedder is None or (model_name and _global_embedder.model_name != model_name):
        _global_embedder = VehicleEmbedder(model_name or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    return _global_embedder