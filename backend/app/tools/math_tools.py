import re
from typing import List, Dict, Any


def extract_tables_from_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agent tool: Filters and extracts markdown tables from retrieved document chunks.
    """
    extracted = []
    for c in chunks:
        content = c.get("content", "")
        if "|" in content and "---" in content:
            table_lines = [line for line in content.split("\n") if "|" in line]
            if len(table_lines) >= 2:
                extracted.append({
                    "filename": c.get("filename"),
                    "page": c.get("page_number"),
                    "section": c.get("section"),
                    "table_markdown": "\n".join(table_lines)
                })
    return extracted


def calculate_statistics(numbers: List[float]) -> Dict[str, float]:
    """
    Agent tool: Computes statistical metrics (sum, mean, min, max, percentage change) for numerical questions.
    """
    if not numbers:
        return {"error": "No numbers provided."}
    
    total = sum(numbers)
    avg = total / len(numbers)
    min_val = min(numbers)
    max_val = max(numbers)
    
    pct_change = 0.0
    if len(numbers) >= 2 and numbers[0] > 0:
        pct_change = ((numbers[-1] - numbers[0]) / numbers[0]) * 100.0

    return {
        "count": len(numbers),
        "sum": round(total, 2),
        "mean": round(avg, 2),
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "percentage_change": round(pct_change, 2)
    }
