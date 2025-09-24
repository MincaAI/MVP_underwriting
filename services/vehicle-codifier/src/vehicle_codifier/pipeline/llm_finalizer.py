"""LLM-based candidate finalizer for vehicle codifier pipeline."""

from typing import List, Optional
from ..models import Candidate, ExtractedFields

def finalize_candidates_with_llm(
    candidates: List[Candidate],
    description: str,
    extracted_fields: ExtractedFields,
    year: int,
    openai_client=None,
    openai_model: str = "gpt-4o-mini"
) -> (List[dict], Optional[str]):
    """
    Take top 10 candidates by final_score, use LLM to select top 3 with confidence.
    Returns up to 3 candidates with LLM confidence scores (0.0-1.0).
    If LLM is unavailable, returns top 3 by final_score and a notice.
    """
    # Sort and take top 10 by final_score
    top_candidates = sorted(candidates, key=lambda c: c.final_score, reverse=True)[:10]
    if not top_candidates:
        return [], "No candidates available"

    if openai_client is None:
        # Fallback: return top 3 by final_score, with notice
        return [
            {
                "candidate": c,
                "llm_confidence": None,
                "llm_notice": "LLM unavailable, using total score"
            }
            for c in top_candidates[:3]
        ], "LLM unavailable, using total score"

    # Prepare prompt for LLM
    candidate_info = [
        {
            "index": i,
            "brand": c.marca,
            "submodel": c.submarca,
            "year": c.modelo,
            "description": c.descveh,
            "vehicletype": c.tipveh
        }
        for i, c in enumerate(top_candidates)
    ]
    prompt = f"""You are a vehicle matching expert. Analyze the following vehicle description and select the top 3 candidates with confidence scores (0.0-1.0).

Vehicle to match:
- Year: {year}
- Description: "{description}"

Candidates:
{candidate_info}

For each of the top 3 candidates, respond with:
- index (from the list above)
- confidence (0.0-1.0, higher is better)

Respond ONLY with valid JSON in this format:
{{
  "finalists": [
    {{"index": 0, "confidence": 0.92}},
    {{"index": 3, "confidence": 0.81}},
    {{"index": 5, "confidence": 0.77}}
  ]
}}
"""

    try:
        response = openai_client.chat.completions.create(
            model=openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.1
        )
        result_text = response.choices[0].message.content.strip()
        import json
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_text = result_text[json_start:json_end] if json_start >= 0 and json_end > json_start else result_text
        result_data = json.loads(json_text)
        finalists = result_data.get("finalists", [])
        # Map LLM results to candidate objects
        results = []
        for finalist in finalists:
            idx = finalist.get("index")
            conf = finalist.get("confidence", 0.0)
            if idx is not None and 0 <= idx < len(top_candidates):
                results.append({
                    "candidate": top_candidates[idx],
                    "llm_confidence": conf,
                    "llm_notice": None
                })
        return results, None
    except Exception as e:
        # Fallback: return top 3 by final_score, with notice
        return [
            {
                "candidate": c,
                "llm_confidence": None,
                "llm_notice": f"LLM error: {e}, using total score"
            }
            for c in top_candidates[:3]
        ], f"LLM error: {e}, using total score"
