import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NEXUS — Enterprise Agentic Document Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "nexus_super_secret_jwt_key_change_in_production_2025_safe_hash"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nexus.db"
    
    # Storage
    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
    UPLOAD_MAX_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "txt", "md"]
    
    # Qdrant Vector Store
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_IN_MEMORY: bool = True
    QDRANT_COLLECTION_NAME: str = "nexus_document_chunks"
    
    # AWS Bedrock & S3 Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "nexus-enterprise-docs"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    BEDROCK_EMBED_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    USE_AWS_BEDROCK: bool = False
    
    # Cost Estimation Tokens
    COST_PER_INPUT_TOKEN_HAIKU: float = 0.00000025
    COST_PER_OUTPUT_TOKEN_HAIKU: float = 0.00000125
    COST_PER_INPUT_TOKEN_SONNET: float = 0.000003
    COST_PER_OUTPUT_TOKEN_SONNET: float = 0.000015
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure local storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
