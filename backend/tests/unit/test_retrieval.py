import pytest
from backend.app.retrieval.hybrid_rrf import reciprocal_rank_fusion
from backend.app.retrieval.reranker import Reranker


def test_reciprocal_rank_fusion_math():
    dense_results = [
        {"chunk_id": "c1", "content": "Text 1", "score": 0.9},
        {"chunk_id": "c2", "content": "Text 2", "score": 0.8},
        {"chunk_id": "c3", "content": "Text 3", "score": 0.7},
    ]
    bm25_results = [
        {"chunk_id": "c2", "content": "Text 2", "score": 5.0},
        {"chunk_id": "c1", "content": "Text 1", "score": 4.0},
        {"chunk_id": "c4", "content": "Text 4", "score": 3.0},
    ]

    fused = reciprocal_rank_fusion(dense_results, bm25_results, rrf_k=60, top_k=4)

    assert len(fused) == 4
    # c1 and c2 appear in both lists, so their RRF scores should be higher than c3 and c4
    top_cids = [f["chunk_id"] for f in fused[:2]]
    assert "c1" in top_cids
    assert "c2" in top_cids
    assert fused[0]["rrf_score"] > fused[2]["rrf_score"]
    assert fused[0]["retrieval_mode"] == "hybrid_rrf"


def test_reranker_execution():
    reranker = Reranker()
    query = "What is the hotel allowance limit?"
    candidates = [
        {"chunk_id": "c1", "content": "The quick brown fox jumps over the lazy dog.", "score": 0.5},
        {"chunk_id": "c2", "content": "Hotel allowance limit is capped at 5000 per night for standard travel.", "score": 0.5},
        {"chunk_id": "c3", "content": "Cybersecurity passwords must be 14 characters.", "score": 0.5},
    ]

    reranked = reranker.rerank(query, candidates, top_k=2)

    assert len(reranked) == 2
    # The chunk discussing hotel allowance limit should rank highest
    assert reranked[0]["chunk_id"] == "c2"
    assert reranked[0]["is_reranked"] is True
    assert reranked[0]["rerank_score"] >= reranked[1]["rerank_score"]
