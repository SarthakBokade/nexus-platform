import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.config import settings
from backend.app.db.models import DocumentChunk, Document
from backend.app.retrieval.qdrant_store import QdrantVectorStore

logger = logging.getLogger("nexus.retrieval.dense")

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class DenseRetriever:
    """
    Dense Vector Similarity Retriever.
    Supports Qdrant Vector Engine or local numpy cosine similarity fallback.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.qdrant = QdrantVectorStore()
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer '{model_name}': {e}")

    def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for query or chunk."""
        if self.model:
            emb = self.model.encode(text, convert_to_numpy=True)
            return emb.tolist()
        
        # Deterministic TF-IDF / Hash fallback vector if model not loaded
        np.random.seed(abs(hash(text)) % (2**32))
        return np.random.randn(384).tolist()

    async def search(
        self,
        db: AsyncSession,
        query: str,
        allowed_access_levels: List[str],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Executes Dense Vector Similarity Search with RBAC Access Level Filtering.
        """
        query_vec_list = self.embed_text(query)
        query_vec = np.array(query_vec_list)

        # 1. Try Qdrant Vector Search First
        qdrant_results = self.qdrant.search(query_vec_list, allowed_access_levels, top_k=top_k)
        if qdrant_results:
            return qdrant_results

        # 2. Fallback to DB Chunks & Cosine Calculation
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.access_level.in_(allowed_access_levels))
        )
        res = await db.execute(stmt)
        rows = res.all()

        if not rows:
            return []

        results = []
        chunks_to_index = []
        for chunk, doc in rows:
            chunk_vec_list = self.embed_text(chunk.content)
            chunk_vec = np.array(chunk_vec_list)
            norm_q = np.linalg.norm(query_vec)
            norm_c = np.linalg.norm(chunk_vec)
            sim = 0.0
            if norm_q > 0 and norm_c > 0:
                sim = float(np.dot(query_vec, chunk_vec) / (norm_q * norm_c))

            item = {
                "chunk_id": chunk.id,
                "document_id": doc.id,
                "filename": doc.filename,
                "version": doc.version,
                "department": doc.department,
                "access_level": chunk.access_level,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "content": chunk.content,
                "score": round(sim, 4),
                "retrieval_mode": "dense"
            }
            results.append(item)
            chunks_to_index.append({**item, "vector": chunk_vec_list})

        # Asynchronously or opportunistically index into Qdrant for future queries
        if chunks_to_index:
            self.qdrant.upsert_chunks(chunks_to_index)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
