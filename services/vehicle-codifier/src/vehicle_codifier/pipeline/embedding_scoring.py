"""Embedding-based candidate scoring for vehicle codifier pipeline (function-based, minimal)."""

from typing import List, Optional, Tuple
import numpy as np

from ..models import Candidate, ExtractedFields
from ..config import get_settings
from ..utils import norm

_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        model_name = get_settings().embedding_model
        _embedder = SentenceTransformer(model_name)
        print(f"✅ Loaded embedding model: {model_name}")
    return _embedder

def generate_embedding(text: str) -> Optional[List[float]]:
    embedder = get_embedder()
    try:
        embedding = embedder.encode([text], normalize_embeddings=True)[0].tolist()
        return embedding
    except Exception as e:
        print(f"⚠️ Embedding generation failed: {e}")
        return None

def build_query_label(modelo: int, fields: ExtractedFields) -> str:
    parts = [f"modelo={modelo}"]
    if fields.marca:
        parts.append(f"marca={norm(fields.marca)}")
    if fields.submarca:
        parts.append(f"submarca={norm(fields.submarca)}")
    if fields.descveh:
        parts.append(f"descveh={norm(fields.descveh)}")
    if fields.tipveh:
        parts.append(f"tipveh={norm(fields.tipveh)}")
    return " | ".join(parts)

def build_label_and_embedding(modelo: int, fields: ExtractedFields) -> Tuple[str, Optional[List[float]]]:
    label = build_query_label(modelo, fields)
    embedding = generate_embedding(label)
    return label, embedding

def score_candidates_with_embedding(
    candidates: List[Candidate],
    description: str
) -> List[Candidate]:
    """
    Scores candidates by embedding similarity to the input description.

    Args:
        candidates: List of Candidate objects to score.
        description: The input vehicle description string.

    Returns:
        List of Candidate objects with updated similarity_score, sorted by similarity_score descending.
    """
    if not candidates or not description:
        return candidates

    desc_embedding = generate_embedding(description)
    print('=====>', description)
    if desc_embedding is None:
        return candidates

    def cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    for candidate in candidates:
        candidate_embedding = getattr(candidate, "embedding", None)
        if candidate_embedding is None:
            candidate.similarity_score = 0.0
        else:
            cos_sim = cosine_similarity(desc_embedding, candidate_embedding)
            candidate.similarity_score = (cos_sim + 1) / 2  # Normalize to [0, 1]

    candidates.sort(key=lambda c: c.similarity_score, reverse=True)
    return candidates
