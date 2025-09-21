"""LLM-based candidate validation and scoring."""

import json
from typing import List, Optional
import openai

from .models import Candidate, ExtractedFields


class LLMValidator:
    """Handles LLM validation and scoring of candidates."""

    def __init__(self, openai_client: Optional[openai.OpenAI], openai_model: str):
        """Initialize the LLM validator with OpenAI client and model."""
        self.openai_client = openai_client
        self.openai_model = openai_model

    def validate_candidates(self, candidates: List[Candidate], description: str,
                          extracted_fields: ExtractedFields, year: int) -> List[Candidate]:
        """Use LLM to validate and score candidates with confidence ratings."""
        if not self.openai_client or not candidates:
            return candidates

        print(f"🤖 Step 4: LLM validation of {len(candidates)} candidates...")

        # Check if these are high-confidence pre-filtered candidates
        # High-confidence candidates should be trusted more and not easily discarded
        has_high_confidence_candidates = any(c.final_score >= 0.9 for c in candidates)

        if has_high_confidence_candidates:
            print(f"🎯 Found high-confidence pre-filtered candidates (score >= 0.9), being more lenient")

        try:
            # Prepare candidates for LLM analysis
            candidate_info = []
            for i, candidate in enumerate(candidates):  # Limit to top 10 for efficiency
                candidate_info.append({
                    "index": i,
                    "cvegs": str(candidate.cvegs),
                    "brand": candidate.marca,
                    "submodel": candidate.submarca,
                    "year": candidate.modelo,
                    "description": candidate.descveh,
                    "current_score": round(candidate.final_score, 3)
                })

            prompt = self._build_validation_prompt(
                description, extracted_fields, year, candidate_info, has_high_confidence_candidates
            )

            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result_data = json.loads(result_text)
                validations = result_data.get("validations", [])

                # Apply LLM confidence scores
                validated_candidates = []
                for validation in validations:
                    idx = validation.get("index")
                    llm_confidence = validation.get("confidence", 0.0)

                    if idx is not None and idx < len(candidates):
                        candidate = candidates[idx]

                        # For high-confidence pre-filtered candidates, be more conservative with LLM blending
                        if candidate.final_score >= 0.9:
                            # Trust the pre-filtering more: 80% original, 20% LLM
                            # Also ensure LLM confidence doesn't drop too much
                            min_llm_confidence = max(llm_confidence, 0.7)  # Don't let LLM go below 0.7 for high-confidence candidates
                            blended_score = (0.8 * candidate.final_score) + (0.2 * min_llm_confidence)
                            print(f"🎯 High-confidence candidate preserved: {candidate.marca} {candidate.submarca} (original: {candidate.final_score:.3f}, LLM: {llm_confidence:.3f}, final: {blended_score:.3f})")
                        else:
                            # Normal blending for regular candidates: 60% original, 40% LLM
                            blended_score = (0.6 * candidate.final_score) + (0.4 * llm_confidence)

                        # Create new candidate with updated score
                        validated_candidate = Candidate(
                            cvegs=candidate.cvegs,
                            marca=candidate.marca,
                            submarca=candidate.submarca,
                            modelo=candidate.modelo,
                            descveh=candidate.descveh,
                            label=candidate.label,
                            similarity_score=candidate.similarity_score,
                            fuzzy_score=candidate.fuzzy_score,
                            final_score=blended_score,
                            cvesegm=candidate.cvesegm,
                            tipveh=candidate.tipveh
                        )
                        validated_candidates.append(validated_candidate)

                # Add remaining candidates without LLM validation (preserve high-confidence ones)
                for i, candidate in enumerate(candidates):
                    if i >= len(validations):
                        # For high-confidence candidates without LLM validation, keep them with slight penalty
                        if candidate.final_score >= 0.9:
                            adjusted_candidate = Candidate(
                                cvegs=candidate.cvegs,
                                marca=candidate.marca,
                                submarca=candidate.submarca,
                                modelo=candidate.modelo,
                                descveh=candidate.descveh,
                                label=candidate.label,
                                similarity_score=candidate.similarity_score,
                                fuzzy_score=candidate.fuzzy_score,
                                final_score=candidate.final_score * 0.95,  # Slight penalty for no LLM validation
                                cvesegm=candidate.cvesegm,
                                tipveh=candidate.tipveh
                            )
                            validated_candidates.append(adjusted_candidate)
                            print(f"🎯 High-confidence candidate preserved without LLM validation: {candidate.marca} {candidate.submarca}")
                        else:
                            validated_candidates.append(candidate)

                # Re-sort by new blended scores
                validated_candidates.sort(key=lambda x: x.final_score, reverse=True)

                if validated_candidates:
                    print(f"✅ LLM validation completed. Top candidate score: {validated_candidates[0].final_score:.3f}")
                else:
                    print(f"⚠️ LLM validation removed all candidates")
                return validated_candidates

            except json.JSONDecodeError:
                print("⚠️ LLM returned invalid JSON, using original candidates")
                return candidates

        except Exception as e:
            print(f"⚠️ LLM validation failed: {e}")
            return candidates

    def _build_validation_prompt(self, description: str, extracted_fields: ExtractedFields,
                               year: int, candidate_info: List[dict],
                               has_high_confidence_candidates: bool) -> str:
        """Build the validation prompt for the LLM."""

        high_confidence_note = ""
        if has_high_confidence_candidates:
            high_confidence_note = "Note: These candidates were pre-filtered with high confidence (>=0.9), so be more lenient in scoring."

        prompt = f"""Analyze this vehicle description and rate how well each candidate matches.

Vehicle to match:
- Year: {year}
- Description: "{description}"
- Extracted brand: {extracted_fields.marca or 'None'}
- Extracted submodel: {extracted_fields.submarca or 'None'}
- Extracted type: {extracted_fields.tipveh or 'None'}

Candidates:
{json.dumps(candidate_info, indent=2)}

For each candidate, provide a confidence score (0.0-1.0) based on:
1. Brand match accuracy
2. Model/submodel compatibility
3. Year appropriateness
4. Vehicle type consistency
5. Overall description alignment

{high_confidence_note}

Return JSON format:
{{
  "validations": [
    {{"index": 0, "confidence": 0.85, "reasoning": "Strong brand and model match"}},
    {{"index": 1, "confidence": 0.65, "reasoning": "Brand matches but submodel differs"}}
  ]
}}"""

        return prompt