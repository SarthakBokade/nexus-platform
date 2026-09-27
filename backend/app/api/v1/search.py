from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.db.models import User
from backend.app.auth.rbac import get_current_user
from backend.app.retrieval.pipeline import HybridRetrievalPipeline

router = APIRouter(prefix="/search", tags=["Hybrid Retrieval"])
retrieval_pipeline = HybridRetrievalPipeline()


class SearchQuerySchema(BaseModel):
    query: str
    mode: str = "hybrid_rerank" # dense, bm25, hybrid, hybrid_rerank
    top_k: int = 5


class SearchResultItemSchema(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    version: str
    department: str
    access_level: str
    page_number: int
    section: Optional[str]
    content: str
    score: float
    retrieval_mode: str


class SearchResponseSchema(BaseModel):
    query: str
    mode: str
    user_role: str
    latency_ms: int
    results_count: int
    results: List[SearchResultItemSchema]


@router.post("", response_model=SearchResponseSchema)
@router.post("/query", response_model=SearchResponseSchema)
async def execute_search_query(
    payload: SearchQuerySchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
        
    try:
        search_data = await retrieval_pipeline.execute_search(
            db=db,
            query=payload.query,
            user=current_user,
            mode=payload.mode,
            top_k=payload.top_k
        )
        return SearchResponseSchema(
            query=search_data["query"],
            mode=search_data["mode"],
            user_role=search_data["user_role"],
            latency_ms=search_data["latency_ms"],
            results_count=search_data["results_count"],
            results=[
                SearchResultItemSchema(
                    chunk_id=r["chunk_id"],
                    document_id=r["document_id"],
                    filename=r["filename"],
                    version=r["version"],
                    department=r["department"],
                    access_level=r["access_level"],
                    page_number=r["page_number"],
                    section=r.get("section"),
                    content=r["content"],
                    score=r["score"],
                    retrieval_mode=r["retrieval_mode"]
                )
                for r in search_data["results"]
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval search failed: {str(e)}")
