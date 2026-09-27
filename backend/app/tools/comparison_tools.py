import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.auth.rbac import User, get_allowed_access_levels
from backend.app.db.models import Document, DocumentChunk
from backend.app.tools.document_tools import search_documents, search_by_metadata


async def compare_documents(
    db: AsyncSession,
    user: User,
    doc_id_1: str,
    doc_id_2: str
) -> Dict[str, Any]:
    """
    Agent tool: Compares two document versions section-by-section and outputs a structured matrix of changes.
    """
    res1 = await db.execute(select(Document).where(Document.id == doc_id_1))
    doc1 = res1.scalars().first()
    res2 = await db.execute(select(Document).where(Document.id == doc_id_2))
    doc2 = res2.scalars().first()

    if not doc1 or not doc2:
        return {"error": "One or both documents not found."}

    chunks1_res = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc1.id).order_by(DocumentChunk.chunk_index))
    chunks1 = chunks1_res.scalars().all()
    chunks2_res = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc2.id).order_by(DocumentChunk.chunk_index))
    chunks2 = chunks2_res.scalars().all()

    # Numeric & Keyword change extraction heuristic
    comparison_matrix = []
    
    # Extract numerical allowances from doc1 and doc2
    num_pattern = r"(₹|\$|\bINR\b|\bUSD\b)\s*([\d,]+)"
    
    vals1 = {}
    for c in chunks1:
        matches = re.findall(num_pattern, c.content)
        for curr, val in matches:
            vals1[c.section or "General"] = f"{curr} {val}"

    vals2 = {}
    for c in chunks2:
        matches = re.findall(num_pattern, c.content)
        for curr, val in matches:
            vals2[c.section or "General"] = f"{curr} {val}"

    all_sections = set(vals1.keys()).union(set(vals2.keys()))
    for sec in all_sections:
        v1 = vals1.get(sec, "N/A")
        v2 = vals2.get(sec, "N/A")
        change_type = "Unchanged"
        if v1 != v2:
            if v1 == "N/A":
                change_type = "Added"
            elif v2 == "N/A":
                change_type = "Removed"
            else:
                change_type = "Increased / Updated"

        comparison_matrix.append({
            "category_section": sec,
            "val_doc1": v1,
            "val_doc2": v2,
            "change": change_type,
            "evidence_doc1": f"{doc1.filename} ({doc1.version})",
            "evidence_doc2": f"{doc2.filename} ({doc2.version})"
        })

    return {
        "doc1": {"id": doc1.id, "filename": doc1.filename, "version": doc1.version},
        "doc2": {"id": doc2.id, "filename": doc2.filename, "version": doc2.version},
        "comparison_matrix": comparison_matrix
    }


async def detect_conflicts(
    db: AsyncSession,
    user: User,
    topic: str
) -> Dict[str, Any]:
    """
    Agent tool: Searches across authorized documents for contradictory statements on a given topic.
    """
    results = await search_documents(db, user, topic, top_k=10)
    if len(results) < 2:
        return {"conflicts_detected": False, "conflict_list": [], "message": "Insufficient documents found on topic to compare."}

    # Group by document and check for numeric or policy variance (e.g. 3 days vs 2 days remote)
    conflicts = []
    
    # Check for remote work day variance
    remote_matches = []
    for item in results:
        match = re.search(r"(\d+)\s+days?\s+per\s+week", item["content"], re.IGNORECASE)
        if match:
            remote_matches.append({
                "filename": item["filename"],
                "version": item["version"],
                "page": item["page_number"],
                "section": item.get("section"),
                "days": int(match.group(1)),
                "excerpt": item["content"][:200] + "..."
            })

    if len(remote_matches) >= 2:
        days_set = set(m["days"] for m in remote_matches)
        if len(days_set) > 1:
            # Conflict detected!
            conflicts.append({
                "topic": topic,
                "conflict_type": "Policy Contradiction",
                "details": f"Different documents specify conflicting limits ({' vs '.join(str(d) + ' days' for d in days_set)}).",
                "evidence": remote_matches
            })

    return {
        "topic": topic,
        "conflicts_detected": len(conflicts) > 0,
        "conflict_list": conflicts
    }
