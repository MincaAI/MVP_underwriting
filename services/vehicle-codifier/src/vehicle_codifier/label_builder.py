"""Vehicle label building and embedding generation module."""

from typing import Optional, List, Tuple
from .models import ExtractedFields
from .config import get_settings
from .utils import norm


class VehicleLabelBuilder:
    """Handle CATVER label building and embedding generation."""

    def __init__(self):
        self.settings = get_settings()
        self.embedder = self._initialize_embedder()

    def _initialize_embedder(self):
        """Initialize the sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer(self.settings.embedding_model)
            print(f"✅ Loaded embedding model: {self.settings.embedding_model}")
            return embedder
        except ImportError:
            print("⚠️ sentence-transformers not available, embeddings will be disabled")
            return None

    def build_query_label(self, modelo: int, fields: ExtractedFields) -> str:
        """Build structured label matching CATVER format used in catalog."""
        parts = []

        # Start with modelo (year) first - same as catalog_load.py
        parts.append(f"modelo={modelo}")

        # Add extracted fields using same order as catalog_load.py
        if fields.marca:
            parts.append(f"marca={norm(fields.marca)}")
        if fields.submarca:
            parts.append(f"submarca={norm(fields.submarca)}")

        # Note: we don't have numver, ramo, cvemarc, cvesubm, martip, idperdiod, sumabas
        # so we'll only include what we can extract

        if fields.cvesegm:
            parts.append(f"cvesegm={norm(fields.cvesegm)}")
        if fields.descveh:
            parts.append(f"descveh={norm(fields.descveh)}")
        if fields.tipveh:
            parts.append(f"tipveh={norm(fields.tipveh)}")

        return " | ".join(parts)

    def generate_embedding(self, query_label: str) -> Optional[List[float]]:
        """Generate embedding vector for query label."""
        if not self.embedder:
            return None

        try:
            embedding = self.embedder.encode(
                [query_label],
                normalize_embeddings=True
            )[0].tolist()
            return embedding
        except Exception as e:
            print(f"⚠️ Embedding generation failed: {e}")
            return None

    def build_label_and_embedding(self, modelo: int, fields: ExtractedFields) -> Tuple[str, Optional[List[float]]]:
        """Complete label building and embedding generation pipeline."""
        # Build structured label
        query_label = self.build_query_label(modelo, fields)

        # Generate embedding for the label
        embedding = self.generate_embedding(query_label)

        return query_label, embedding

    def generate_batch_embeddings(self, query_labels: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple labels efficiently."""
        if not self.embedder:
            return [None] * len(query_labels)

        try:
            embeddings = self.embedder.encode(
                query_labels,
                normalize_embeddings=True
            )
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            print(f"⚠️ Batch embedding generation failed: {e}")
            return [None] * len(query_labels)

    def get_health_status(self) -> dict:
        """Get label builder health status."""
        return {
            "embedder_available": self.embedder is not None,
            "embedding_model": self.settings.embedding_model,
            "embedding_dimension": self.settings.embedding_dimension
        }