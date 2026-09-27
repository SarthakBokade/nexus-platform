import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.rbac import User, get_allowed_access_levels
from backend.app.retrieval.dense import DenseRetriever
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.hybrid_rrf import reciprocal_rank_fusion
from backend.app.retrieval.reranker import Reranker

logger = logging.getLogger("nexus.retrieval.pipeline")


class HybridRetrievalPipeline:

    def __init__(self):
        self.dense_retriever = DenseRetriever()
        self.bm25_retriever = BM25Retriever()
        self.reranker = Reranker()

    async def execute_search(
        self,
        db: AsyncSession,
        query: str,
        user: User,
        mode: str = "hybrid_rerank", # dense, bm25, hybrid, hybrid_rerank
        top_k: int = 5
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        # 1. Enforce RBAC Pre-Retrieval Filter
        allowed_access_levels = get_allowed_access_levels(user.role)

        dense_candidates = []
        bm25_candidates = []
        fused_candidates = []
        final_chunks = []

        # 2. Dense Retrieval
        if mode in ["dense", "hybrid", "hybrid_rerank"]:
            dense_candidates = await self.dense_retriever.search(
                db, query, allowed_access_levels, top_k=20
            )

        # 3. BM25 Retrieval
        if mode in ["bm25", "hybrid", "hybrid_rerank"]:
            bm25_candidates = await self.bm25_retriever.search(
                db, query, allowed_access_levels, top_k=20
            )

        # 4. Fusion / Routing
        if mode == "dense":
            final_chunks = dense_candidates[:top_k]
        elif mode == "bm25":
            final_chunks = bm25_candidates[:top_k]
        elif mode == "hybrid":
            fused_candidates = reciprocal_rank_fusion(dense_candidates, bm25_candidates, top_k=top_k)
            final_chunks = fused_candidates
        elif mode == "hybrid_rerank":
            fused_candidates = reciprocal_rank_fusion(dense_candidates, bm25_candidates, top_k=20)
            final_chunks = self.reranker.rerank(query, fused_candidates, top_k=top_k)

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "query": query,
            "mode": mode,
            "user_role": user.role,
            "allowed_access_levels": allowed_access_levels,
            "latency_ms": latency_ms,
            "dense_count": len(dense_candidates),
            "bm25_count": len(bm25_candidates),
            "fused_count": len(fused_candidates),
            "results_count": len(final_chunks),
            "results": final_chunks
        }
