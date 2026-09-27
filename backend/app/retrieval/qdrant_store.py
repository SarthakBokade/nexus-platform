import logging
from typing import List, Dict, Any, Optional
import numpy as np

from backend.app.config import settings

logger = logging.getLogger("nexus.retrieval.qdrant")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False


class QdrantVectorStore:
    """
    Production-grade Qdrant Vector Engine interface with RBAC payload pre-filtering.
    Supports in-memory ephemeral mode or networked cluster deployment.
    """

    COLLECTION_NAME = "nexus_documents"
    VECTOR_DIM = 384

    def __init__(self):
        self.client: Optional[Any] = None
        self._initialize_client()

    def _initialize_client(self):
        if not HAS_QDRANT:
            logger.warning("qdrant-client package not available. Operating in fallback mode.")
            return

        try:
            if settings.QDRANT_IN_MEMORY:
                self.client = QdrantClient(":memory:")
                logger.info("Initialized Qdrant in-memory vector store.")
            else:
                self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=5.0)
                logger.info(f"Connected to Qdrant cluster at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

            # Ensure collection exists
            self._ensure_collection()
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant, falling back to local vector memory: {e}")
            self.client = QdrantClient(":memory:")
            self._ensure_collection()

    def _ensure_collection(self):
        if not self.client:
            return
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.COLLECTION_NAME for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=qmodels.VectorParams(
                        size=self.VECTOR_DIM,
                        distance=qmodels.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection '{self.COLLECTION_NAME}' (dim={self.VECTOR_DIM}, metric=Cosine)")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")

    def upsert_chunks(self, chunks_with_vectors: List[Dict[str, Any]]) -> bool:
        """
        Upserts document chunks with their dense vectors and RBAC security metadata.
        """
        if not self.client or not chunks_with_vectors:
            return False

        try:
            points = []
            for item in chunks_with_vectors:
                cid = item["chunk_id"]
                vec = item["vector"]
                payload = {
                    "chunk_id": cid,
                    "document_id": item.get("document_id"),
                    "filename": item.get("filename"),
                    "version": item.get("version"),
                    "department": item.get("department"),
                    "access_level": item.get("access_level"),
                    "page_number": item.get("page_number"),
                    "section": item.get("section"),
                    "content": item.get("content")
                }
                points.append(qmodels.PointStruct(
                    id=abs(hash(cid)) % (2**63), # 64-bit integer ID for Qdrant
                    vector=vec,
                    payload=payload
                ))

            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points
            )
            logger.info(f"Successfully indexed {len(points)} chunks into Qdrant collection '{self.COLLECTION_NAME}'")
            return True
        except Exception as e:
            logger.error(f"Error upserting vectors to Qdrant: {e}")
            return False

    def search(
        self,
        query_vector: List[float],
        allowed_access_levels: List[str],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Executes Vector Cosine Search with Pre-Retrieval RBAC Payload Filtering.
        """
        if not self.client:
            return []

        try:
            # Construct RBAC pre-filter
            rbac_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="access_level",
                        match=qmodels.MatchAny(any=allowed_access_levels)
                    )
                ]
            )

            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.COLLECTION_NAME,
                    query=query_vector,
                    query_filter=rbac_filter,
                    limit=top_k
                )
                results = response.points
            else:
                results = self.client.search(
                    collection_name=self.COLLECTION_NAME,
                    query_vector=query_vector,
                    query_filter=rbac_filter,
                    limit=top_k
                )

            formatted = []
            for hit in results:
                p = hit.payload or {}
                formatted.append({
                    "chunk_id": p.get("chunk_id"),
                    "document_id": p.get("document_id"),
                    "filename": p.get("filename"),
                    "version": p.get("version"),
                    "department": p.get("department"),
                    "access_level": p.get("access_level"),
                    "page_number": p.get("page_number"),
                    "section": p.get("section"),
                    "content": p.get("content"),
                    "score": round(float(hit.score), 4),
                    "retrieval_mode": "dense_qdrant"
                })

            return formatted
        except Exception as e:
            logger.warning(f"Qdrant vector search failed, returning empty set: {e}")
            return []
