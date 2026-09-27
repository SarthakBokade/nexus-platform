"""
SageMaker Embeddings Service — Phase 3

Drop-in replacement for the local sentence-transformers embedder.
Calls an Amazon SageMaker real-time inference endpoint hosting a
sentence-transformers model (e.g. all-MiniLM-L6-v2 or BGE-large).

Architecture Decision:
- Local sentence-transformers is used during development and when
  AWS credentials are not present (zero-cost, offline).
- SageMaker endpoint is activated via env var USE_SAGEMAKER_EMBEDDINGS=true
  and SAGEMAKER_ENDPOINT_NAME=nexus-embedder-v1.
- This allows a seamless switch to production-grade GPU-backed embeddings
  without changing any retrieval/ingestion code.

Why SageMaker vs Bedrock Titan Embeddings?
- SageMaker: Full control over model version, batch size, instance type.
- Bedrock Titan: Managed, less control, good for quick start.
- NEXUS supports both paths.
"""
import logging
import json
from typing import List, Optional
import numpy as np
from backend.app.config import settings

logger = logging.getLogger("nexus.services.sagemaker_embeddings")

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False


class EmbeddingService:
    """
    Unified embedding service with automatic fallback chain:
      1. Amazon SageMaker real-time endpoint (if configured + AWS creds)
      2. Amazon Bedrock Titan Embeddings (if USE_AWS_BEDROCK=true)
      3. Local sentence-transformers (always available, offline)

    Usage:
        svc = EmbeddingService()
        vector = svc.embed("What is the travel policy?")         # single
        vectors = svc.embed_batch(["text1", "text2", "text3"])   # batch
    """

    EMBEDDING_DIM = 384   # all-MiniLM-L6-v2 output dimension
    LOCAL_MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self):
        self._local_model: Optional[object] = None
        self._sagemaker_client = None
        self._bedrock_client = None
        self._active_backend: str = "local"

        self._initialize()

    def _initialize(self):
        """Determines the active embedding backend at startup."""
        # Try SageMaker first
        sagemaker_endpoint = getattr(settings, "SAGEMAKER_ENDPOINT_NAME", None)
        use_sagemaker = getattr(settings, "USE_SAGEMAKER_EMBEDDINGS", False)

        if use_sagemaker and sagemaker_endpoint and HAS_BOTO3:
            try:
                self._sagemaker_client = boto3.client(
                    "sagemaker-runtime",
                    region_name=settings.AWS_REGION
                )
                self._active_backend = "sagemaker"
                logger.info(f"Embedding backend: SageMaker endpoint '{sagemaker_endpoint}'")
                return
            except Exception as e:
                logger.warning(f"SageMaker init failed: {e}. Falling back.")

        # Try Bedrock Titan Embeddings
        if settings.USE_AWS_BEDROCK and HAS_BOTO3:
            try:
                self._bedrock_client = boto3.client(
                    "bedrock-runtime",
                    region_name=settings.AWS_REGION
                )
                self._active_backend = "bedrock_titan"
                logger.info("Embedding backend: Amazon Bedrock Titan Embeddings V2")
                return
            except Exception as e:
                logger.warning(f"Bedrock init failed: {e}. Falling back to local.")

        # Local sentence-transformers
        if HAS_ST:
            self._local_model = SentenceTransformer(self.LOCAL_MODEL_NAME)
            self._active_backend = "local"
            logger.info(f"Embedding backend: local sentence-transformers ({self.LOCAL_MODEL_NAME})")
        else:
            self._active_backend = "zero_vector"
            logger.warning("No embedding backend available. Using zero-vectors (retrieval will not work).")

    @property
    def active_backend(self) -> str:
        return self._active_backend

    def embed(self, text: str) -> List[float]:
        """Embed a single text string. Returns a float list of length EMBEDDING_DIM."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts. Returns list of float vectors."""
        if self._active_backend == "sagemaker":
            return self._embed_sagemaker(texts)
        elif self._active_backend == "bedrock_titan":
            return [self._embed_bedrock_titan(t) for t in texts]
        elif self._active_backend == "local" and self._local_model:
            embeddings = self._local_model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        else:
            # Zero-vector fallback (should never hit in normal operation)
            return [[0.0] * self.EMBEDDING_DIM for _ in texts]

    def _embed_sagemaker(self, texts: List[str]) -> List[List[float]]:
        """
        Calls SageMaker real-time inference endpoint.
        Expected endpoint input/output format:
          Input:  {"inputs": ["text1", "text2"]}
          Output: [[0.1, 0.2, ...], [0.3, 0.4, ...]]
        """
        endpoint_name = getattr(settings, "SAGEMAKER_ENDPOINT_NAME", "nexus-embedder-v1")
        try:
            payload = json.dumps({"inputs": texts})
            response = self._sagemaker_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType="application/json",
                Body=payload,
            )
            result = json.loads(response["Body"].read().decode("utf-8"))

            # Handle {"embeddings": [...]} or direct list format
            if isinstance(result, dict) and "embeddings" in result:
                return result["embeddings"]
            return result
        except Exception as e:
            logger.error(f"SageMaker embedding failed: {e}. Falling back to local.")
            if HAS_ST and self._local_model is None:
                self._local_model = SentenceTransformer(self.LOCAL_MODEL_NAME)
            if self._local_model:
                return self._local_model.encode(texts, normalize_embeddings=True).tolist()
            return [[0.0] * self.EMBEDDING_DIM for _ in texts]

    def _embed_bedrock_titan(self, text: str) -> List[float]:
        """
        Calls Amazon Bedrock Titan Embeddings Text V2.
        Model ID: amazon.titan-embed-text-v2:0
        Output dimension: 1024 (configurable to 256/512/1024)
        """
        try:
            body = json.dumps({
                "inputText": text,
                "dimensions": 384,
                "normalize": True,
            })
            response = self._bedrock_client.invoke_model(
                modelId=settings.BEDROCK_EMBED_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read().decode("utf-8"))
            return result["embedding"]
        except Exception as e:
            logger.error(f"Bedrock Titan embedding failed: {e}.")
            return [0.0] * self.EMBEDDING_DIM

    def get_backend_info(self) -> dict:
        """Returns info about the active backend for observability endpoints."""
        return {
            "active_backend": self._active_backend,
            "embedding_dimension": self.EMBEDDING_DIM,
            "model_name": {
                "local": self.LOCAL_MODEL_NAME,
                "sagemaker": getattr(settings, "SAGEMAKER_ENDPOINT_NAME", "N/A"),
                "bedrock_titan": settings.BEDROCK_EMBED_MODEL_ID,
                "zero_vector": "N/A",
            }.get(self._active_backend, "unknown"),
            "fallback_chain": ["sagemaker", "bedrock_titan", "local", "zero_vector"],
        }


# Module-level singleton
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Returns the singleton EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
