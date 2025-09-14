from typing import Literal

def decision_for(score: float, t_high: float, t_low: float) -> Literal["auto_accept", "needs_review", "no_match"]:
    """
    Make decision based on confidence score and thresholds.
    
    Args:
        score: Confidence score (0.0 to 1.0)
        t_high: High threshold for auto-acceptance
        t_low: Low threshold for review requirement
        
    Returns:
        Decision: "auto_accept", "needs_review", or "no_match"
    """
    if score >= t_high:
        return "auto_accept"
    if score >= t_low:
        return "needs_review"
    return "no_match"