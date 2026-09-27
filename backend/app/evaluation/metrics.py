import math
from typing import List, Dict, Any


def calculate_recall_at_k(retrieved_filenames: List[str], expected_filename: str, k: int = 5) -> float:
    top_k = retrieved_filenames[:k]
    return 1.0 if expected_filename in top_k else 0.0


def calculate_precision_at_k(retrieved_filenames: List[str], expected_filename: str, k: int = 5) -> float:
    top_k = retrieved_filenames[:k]
    hits = sum(1 for fn in top_k if fn == expected_filename)
    return hits / float(k)


def calculate_mrr(retrieved_filenames: List[str], expected_filename: str) -> float:
    for idx, fn in enumerate(retrieved_filenames, 1):
        if fn == expected_filename:
            return 1.0 / float(idx)
    return 0.0


def calculate_ndcg(retrieved_filenames: List[str], expected_filename: str, k: int = 5) -> float:
    top_k = retrieved_filenames[:k]
    dcg = 0.0
    for idx, fn in enumerate(top_k, 1):
        rel = 1.0 if fn == expected_filename else 0.0
        dcg += (2**rel - 1) / math.log2(idx + 1)
    
    # Ideal DCG for 1 relevant document
    idcg = (2**1.0 - 1) / math.log2(1 + 1)
    return dcg / idcg if idcg > 0 else 0.0


def calculate_faithfulness(generated_text: str, keywords: List[str]) -> float:
    if not keywords:
        return 1.0
    matches = sum(1 for kw in keywords if kw.lower() in generated_text.lower())
    return matches / float(len(keywords))
