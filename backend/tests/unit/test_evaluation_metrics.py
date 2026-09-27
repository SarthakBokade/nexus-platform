import pytest
from backend.app.evaluation.metrics import (
    calculate_recall_at_k,
    calculate_precision_at_k,
    calculate_mrr,
    calculate_ndcg,
    calculate_faithfulness
)


def test_recall_at_k():
    retrieved = ["doc_a.pdf", "doc_b.pdf", "doc_c.pdf"]
    assert calculate_recall_at_k(retrieved, "doc_a.pdf", k=1) == 1.0
    assert calculate_recall_at_k(retrieved, "doc_b.pdf", k=1) == 0.0
    assert calculate_recall_at_k(retrieved, "doc_b.pdf", k=2) == 1.0
    assert calculate_recall_at_k(retrieved, "doc_z.pdf", k=5) == 0.0


def test_precision_at_k():
    retrieved = ["doc_a.pdf", "doc_b.pdf", "doc_a.pdf", "doc_c.pdf", "doc_d.pdf"]
    # 2 hits for doc_a in top 5
    assert calculate_precision_at_k(retrieved, "doc_a.pdf", k=5) == 0.4
    assert calculate_precision_at_k(retrieved, "doc_b.pdf", k=5) == 0.2
    assert calculate_precision_at_k(retrieved, "doc_z.pdf", k=5) == 0.0


def test_mrr():
    # doc_a at rank 1 -> 1/1 = 1.0
    assert calculate_mrr(["doc_a.pdf", "doc_b.pdf", "doc_c.pdf"], "doc_a.pdf") == 1.0
    # doc_b at rank 2 -> 1/2 = 0.5
    assert calculate_mrr(["doc_a.pdf", "doc_b.pdf", "doc_c.pdf"], "doc_b.pdf") == 0.5
    # doc_c at rank 3 -> 1/3 = 0.3333...
    assert round(calculate_mrr(["doc_a.pdf", "doc_b.pdf", "doc_c.pdf"], "doc_c.pdf"), 4) == 0.3333
    # not found -> 0.0
    assert calculate_mrr(["doc_a.pdf", "doc_b.pdf"], "doc_z.pdf") == 0.0


def test_ndcg():
    # If the target is at rank 1, NDCG is 1.0
    assert calculate_ndcg(["doc_a.pdf", "doc_b.pdf", "doc_c.pdf"], "doc_a.pdf", k=3) == 1.0
    # If the target is at rank 2, NDCG is lower
    ndcg_rank2 = calculate_ndcg(["doc_b.pdf", "doc_a.pdf", "doc_c.pdf"], "doc_a.pdf", k=3)
    assert 0.0 < ndcg_rank2 < 1.0
    # If target not retrieved in top k, NDCG is 0.0
    assert calculate_ndcg(["doc_b.pdf", "doc_c.pdf"], "doc_a.pdf", k=2) == 0.0


def test_faithfulness():
    text = "The international travel reimbursement limit is $350 per night under the 2025 policy."
    keywords = ["$350", "international travel", "2025 policy"]
    assert calculate_faithfulness(text, keywords) == 1.0
    
    partial_keywords = ["$350", "international travel", "unapproved", "first class"]
    assert calculate_faithfulness(text, partial_keywords) == 0.5
