from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.auth.rbac import User, check_document_access, get_allowed_access_levels
from backend.app.db.models import Document, DocumentChunk
from backend.app.retrieval.pipeline import HybridRetrievalPipeline

retrieval_pipeline = HybridRetrievalPipeline()


async def search_documents(
    db: AsyncSession,
    user: User,
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Agent tool: Searches authorized document database using Hybrid Retrieval & Reranking.
    """
    res = await retrieval_pipeline.execute_search(db, query, user, mode="hybrid_rerank", top_k=top_k)
    return res["results"]


async def search_by_metadata(
    db: AsyncSession,
    user: User,
    department: Optional[str] = None,
    document_type: Optional[str] = None,
    version: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Agent tool: Searches documents by metadata attributes (department, version, document_type).
    """
    allowed_access_levels = get_allowed_access_levels(user.role)
    query = select(Document).where(Document.access_level.in_(allowed_access_levels))
    
    if department:
        query = query.where(Document.department == department)
    if document_type:
        query = query.where(Document.document_type == document_type)
    if version:
        query = query.where(Document.version == version)

    res = await db.execute(query)
    docs = res.scalars().all()
    
    return [
        {
            "document_id": d.id,
            "filename": d.filename,
            "version": d.version,
            "department": d.department,
            "document_type": d.document_type,
            "effective_date": d.effective_date,
            "access_level": d.access_level,
            "page_count": d.page_count,
            "summary": d.summary
        }
        for d in docs
    ]


async def retrieve_document(db: AsyncSession, user: User, document_id: str) -> Optional[Dict[str, Any]]:
    """
    Agent tool: Retrieves full text content and metadata of a specific document.
    """
    res = await db.execute(select(Document).where(Document.id == document_id))
    doc = res.scalars().first()
    if not doc:
        return None
        
    if not check_document_access(user, doc.access_level, doc.department):
        return {"error": f"Unauthorized access to document '{doc.filename}' for role '{user.role}'."}

    chunks_res = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index))
    chunks = chunks_res.scalars().all()

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "version": doc.version,
        "department": doc.department,
        "effective_date": doc.effective_date,
        "access_level": doc.access_level,
        "full_text": "\n\n".join([c.content for c in chunks]),
        "chunks": [{"page": c.page_number, "section": c.section, "content": c.content} for c in chunks]
    }
