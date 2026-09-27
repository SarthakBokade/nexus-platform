import logging
from typing import List, Dict, Any

logger = logging.getLogger("nexus.retrieval.reranker")

try:
    from flashrank import Ranker, RerankRequest
    HAS_FLASHRANK = True
except ImportError:
    HAS_FLASHRANK = False


class Reranker:
    """
    CrossEncoder / FlashRank candidate reranker.
    Re-scores Top-20 candidates and returns Top-K highest relevance chunks.
    """

    def __init__(self):
        self.ranker = None
        if HAS_FLASHRANK:
            try:
                self.ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")
            except Exception as e:
                logger.warning(f"Could not load FlashRank ranker: {e}")

    def rerank(self, query: str, candidate_chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        if not candidate_chunks:
            return []

        if self.ranker and HAS_FLASHRANK:
            try:
                passages = [{"id": c["chunk_id"], "text": c["content"]} for c in candidate_chunks]
                req = RerankRequest(query=query, passages=passages)
                ranked_passages = self.ranker.rerank(req)
                
                score_map = {p["id"]: p["score"] for p in ranked_passages}
                reranked = []
                for chunk in candidate_chunks:
                    c_copy = chunk.copy()
                    c_copy["rerank_score"] = round(score_map.get(chunk["chunk_id"], chunk.get("score", 0.0)), 4)
                    c_copy["score"] = c_copy["rerank_score"]
                    c_copy["is_reranked"] = True
                    reranked.append(c_copy)
                
                reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
                return reranked[:top_k]
            except Exception as e:
                logger.warning(f"FlashRank reranking failed, using fallback: {e}")

        # Fallback Reranking Heuristic (exact phrase boost + title match)
        reranked = []
        q_lower = query.lower()
        q_words = set(q_lower.split())

        for chunk in candidate_chunks:
            c_copy = chunk.copy()
            content_lower = chunk["content"].lower()
            
            # Phrase match boost
            phrase_boost = 0.5 if q_lower in content_lower else 0.0
            word_overlap = len(q_words.intersection(set(content_lower.split()))) / max(len(q_words), 1)
            
            final_score = chunk.get("score", 0.5) * 0.5 + word_overlap * 0.3 + phrase_boost * 0.2
            c_copy["rerank_score"] = round(final_score, 4)
            c_copy["score"] = c_copy["rerank_score"]
            c_copy["is_reranked"] = True
            reranked.append(c_copy)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]
