from typing import List, Tuple
from rapidfuzz import fuzz

def rerank(
    qlabel: str,
    candidates: List[Tuple[str, float, str]],  # (cvegs, embed_score, label)
    w_embed: float = 0.7,
    w_lex: float = 0.3,
) -> List[Tuple[str, float, str]]:
    """
    Rerank candidates by blending embedding and lexical similarity scores.
    
    Args:
        qlabel: Query label string
        candidates: List of (cvegs, embedding_score, label) tuples
        w_embed: Weight for embedding score (default 0.7)
        w_lex: Weight for lexical score (default 0.3)
        
    Returns:
        Reranked list sorted by combined score (highest first)
    """
    out = []
    for cvegs, embed_s, label in candidates:
        # lexical similarity (normalized 0..1)
        lex = fuzz.token_set_ratio(qlabel, label) / 100.0
        score = w_embed * embed_s + w_lex * lex
        out.append((cvegs, score, label))
    # highest first
    return sorted(out, key=lambda x: x[1], reverse=True)