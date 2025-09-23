"""Fuzzy matching utility for candidate scoring."""

from typing import List
from ..models import Candidate

try:
    from rapidfuzz.fuzz import ratio
except ImportError:
    # Fallback to difflib if rapidfuzz is not installed
    from difflib import SequenceMatcher
    def ratio(a, b):
        return int(SequenceMatcher(None, a, b).ratio() * 100)

def apply_fuzzy_matching(candidates: List[Candidate], input_description: str) -> List[Candidate]:
    """
    Assigns a fuzzy_score to each candidate based on similarity to the input description.
    The score is normalized to [0, 1].
    """
    for candidate in candidates:
        candidate_desc = candidate.descveh or ""
        # Use rapidfuzz ratio (or fallback) for string similarity
        score = ratio(input_description, candidate_desc)
        candidate.fuzzy_score = score / 100.0  # Normalize to [0, 1]
    return candidates
