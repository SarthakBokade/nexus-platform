from typing import List, Dict, Any


def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    rrf_k: int = 60,
    top_k: int = 20
) -> List[Dict[str, Any]]:
    """
    Combines dense and lexical search result lists using Reciprocal Rank Fusion (RRF).
    RRF Score = 1 / (k + rank_dense) + 1 / (k + rank_bm25)
    """
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict[str, Any]] = {}

    # Process Dense Ranks
    for rank, item in enumerate(dense_results):
        cid = item["chunk_id"]
        chunk_map[cid] = item
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + (rank + 1)))

    # Process BM25 Ranks
    for rank, item in enumerate(bm25_results):
        cid = item["chunk_id"]
        if cid not in chunk_map:
            chunk_map[cid] = item
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + (rank + 1)))

    fused_results = []
    for cid, rrf_score in scores.items():
        item = chunk_map[cid].copy()
        item["rrf_score"] = round(rrf_score, 6)
        item["score"] = round(rrf_score, 6)
        item["retrieval_mode"] = "hybrid_rrf"
        fused_results.append(item)

    fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused_results[:top_k]
