"""Enhanced LLM-based candidate reranking and validation."""

import json
from typing import List, Optional
import openai

from ..models import Candidate, ExtractedFields

class LLMReranker:
    """Handles LLM-based candidate reranking and validation."""

    def __init__(self, openai_client: Optional[openai.OpenAI], openai_model: str):
        self.openai_client = openai_client
        self.openai_model = openai_model

    @staticmethod
    def rerank_top_candidates(
        candidates: List[Candidate],
        description: str,
        extracted_fields: ExtractedFields,
        year: int,
        llm_reranker: "LLMReranker"
    ) -> List[Candidate]:
        """
        Sorts candidates by similarity, takes top 20, and assigns LLM scores using the LLM reranker.
        """
        if not candidates:
            return []
        top_candidates = sorted(
            candidates, key=lambda c: getattr(c, "similarity_score", 0), reverse=True
        )[:20]
        if not top_candidates:
            return []
        return llm_reranker.rerank_candidates(
            top_candidates, description, extracted_fields, year
        )

    def rerank_candidates(
        self,
        candidates: List[Candidate],
        description: str,
        extracted_fields: ExtractedFields,
        year: int,
        threshold_based: bool = False
    ) -> List[Candidate]:
        """
        Use LLM to assign confidence scores to candidates (llm_score).
        Does NOT blend into final_score; llm_score is set for later mixing.
        """
        if not self.openai_client or not candidates:
            return candidates

        try:
            candidate_info = [
                {
                    "index": i,
                    "brand": c.marca,
                    "submodel": c.submarca,
                    "year": c.modelo,
                    "description": c.descveh,
                    "vehicletype": c.tipveh
                }
                for i, c in enumerate(candidates)
            ]

            prompt = self._build_reranking_prompt(
                description, extracted_fields, year, candidate_info
            )

            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )

            result_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            json_text = result_text[json_start:json_end] if json_start >= 0 and json_end > json_start else result_text
            result_data = json.loads(json_text)
            validations = result_data.get("validations", [])

            # Assign LLM confidence scores to llm_score, do not blend into final_score
            for validation in validations:
                idx = validation.get("index")
                llm_confidence = validation.get("confidence", 0.0)
                if idx is not None and idx < len(candidates):
                    candidates[idx].llm_score = llm_confidence

            return candidates

        except Exception:
            # Fallback: assign default llm_score
            for c in candidates:
                c.llm_score = 0.0
            return candidates

    def _build_reranking_prompt(
        self,
        description: str,
        extracted_fields: ExtractedFields,
        year: int,
        candidate_info: List[dict]
    ) -> str:
        """
        Build a concise reranking prompt for the LLM.
        """
        prompt = f"""You are a vehicle matching expert. Analyze the following vehicle description and rate how well each candidate matches.

Vehicle to match:
- Year: {year}
- Description: "{description}"

Candidates:
{json.dumps(candidate_info, indent=2)}

Rate each candidate on a scale of 0.0 to 1.0 based on:
1. Brand match accuracy
2. Model/submodel compatibility
3. Year appropriateness
4. Vehicle type consistency
5. Overall description alignment

Respond ONLY with valid JSON in this format:
{{
  "validations": [
    {{"index": 0, "confidence": 0.85}},
    {{"index": 1, "confidence": 0.65}}
  ]
}}
"""
        return prompt

    def get_health_status(self) -> dict:
        return {
            "reranker_available": self.openai_client is not None,
            "openai_model": self.openai_model if self.openai_client else None
        }

    def is_available(self) -> bool:
        return self.openai_client is not None
