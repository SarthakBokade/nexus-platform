import re
from typing import List, Dict, Any, Tuple


class VerificationAgent:
    """
    Verification & Claim Grounding Layer.
    Deconstructs LLM responses into factual claims, verifies them against retrieved evidence chunks,
    calculates a Grounding Score, and attaches verified source citations.
    """

    def verify_and_ground_response(
        self,
        raw_answer: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Deconstructs response into claims, matches against retrieved chunks, and calculates grounding metrics.
        """
        if not retrieved_chunks:
            return {
                "verified_answer": "Insufficient evidence found in the available documents to answer this query.",
                "grounding_score": 0.0,
                "verification_status": "unverified",
                "citations": [],
                "unsupported_claims": ["No evidence chunks retrieved."]
            }

        # 1. Extract factual claims (sentences with monetary values, dates, limits, or rules)
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", raw_answer) if len(s.strip()) > 10]
        
        verified_claims = []
        unsupported_claims = []
        citations = []

        combined_evidence = " ".join([c["content"] for c in retrieved_chunks]).lower()

        for s in sentences:
            s_lower = s.lower()
            # Extract key words/numbers
            numbers = re.findall(r"\d+", s_lower)
            words = set(re.findall(r"\b[a-z]{4,}\b", s_lower))
            
            # Match against evidence chunks
            matched_chunk = None
            for chunk in retrieved_chunks:
                chunk_text = chunk["content"].lower()
                num_match = all(n in chunk_text for n in numbers) if numbers else True
                word_match = len(words.intersection(set(re.findall(r"\b[a-z]{4,}\b", chunk_text)))) >= max(1, len(words) // 2)
                
                if num_match and word_match:
                    matched_chunk = chunk
                    break

            if matched_chunk:
                verified_claims.append(s)
                cit = {
                    "document_name": matched_chunk["filename"],
                    "version": matched_chunk["version"],
                    "page": matched_chunk["page_number"],
                    "section": matched_chunk.get("section", "General"),
                    "excerpt": matched_chunk["content"][:180] + "..."
                }
                if cit not in citations:
                    citations.append(cit)
            else:
                # Claim not directly found in context
                unsupported_claims.append(s)

        grounding_score = len(verified_claims) / max(len(sentences), 1)
        grounding_score = round(min(1.0, max(0.0, grounding_score)), 2)

        final_answer = raw_answer
        if grounding_score < 0.5:
            final_answer += "\n\n*Note: Insufficient direct evidence found for some claims in the available authorized documents.*"

        return {
            "verified_answer": final_answer,
            "grounding_score": grounding_score,
            "verification_status": "verified" if grounding_score >= 0.8 else "partially_grounded",
            "citations": citations,
            "verified_claims_count": len(verified_claims),
            "unsupported_claims_count": len(unsupported_claims)
        }
