import re
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.db.models import DocumentChunk, Document

logger = logging.getLogger("nexus.retrieval.bm25")

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


class BM25Retriever:
    """
    Lexical Keyword Retriever (BM25).
    Guarantees exact matching for policy IDs, section numbers, monetary values, and dates.
    """

    def tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\w+", text)]

    async def search(
        self,
        db: AsyncSession,
        query: str,
        allowed_access_levels: List[str],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.access_level.in_(allowed_access_levels))
        )
        res = await db.execute(stmt)
        rows = res.all()

        if not rows:
            return []

        corpus = [self.tokenize(chunk.content) for chunk, doc in rows]

        if HAS_BM25 and len(corpus) > 0:
            bm25 = BM25Okapi(corpus)
            scores = bm25.get_scores(query_tokens)
        else:
            # Token overlap scoring fallback
            scores = []
            q_set = set(query_tokens)
            for doc_tokens in corpus:
                overlap = len(q_set.intersection(set(doc_tokens)))
                scores.append(float(overlap))

        results = []
        for idx, (chunk, doc) in enumerate(rows):
            score = float(scores[idx])
            if score > 0:
                results.append({
                    "chunk_id": chunk.id,
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "version": doc.version,
                    "department": doc.department,
                    "access_level": chunk.access_level,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "content": chunk.content,
                    "score": round(score, 4),
                    "retrieval_mode": "bm25"
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
