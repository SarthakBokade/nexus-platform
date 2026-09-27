# NEXUS — Production Deployment & Cloud Operations Guide

---

## 1. Local Development & Container Deployment

### Local Development Mode
```powershell
# 1. Create and activate Python 3.13 venv
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate sample documents & initialize DB
python sample_data/generate_sample_pdfs.py

# 4. Start Uvicorn development server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Docker Compose Deployment
```bash
# Build and start services in background
docker compose up --build -d

# Verify container health
docker compose ps

# View backend logs
docker compose logs -f nexus-backend
```

---

## 2. Production AWS Cloud Architecture

```
                  +-----------------------------------+
                  |          Amazon Route 53          |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------+-----------------+
                  |      Application Load Balancer    |
                  +-----------------+-----------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------+-----------+                       +-----------+-----------+
| ECS Fargate Task 1    |                       | ECS Fargate Task 2    |
| (FastAPI + FlashRank) |                       | (FastAPI + FlashRank) |
+-----------+-----------+                       +-----------+-----------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
             +----------------------+----------------------+
             |                      |                      |
             v                      v                      v
     +-------+-------+      +-------+-------+      +-------+-------+
     |   Amazon S3   |      |   Amazon RDS  |      | Amazon Bedrock|
     | (PDF Storage) |      | (PostgreSQL)  |      | (Claude 3.5 & |
     |               |      |  (pgvector)   |      |  Titan Embed) |
     +---------------+      +---------------+      +---------------+
```

### Infrastructure Components

1. **FastAPI Application on AWS ECS Fargate**:
   * Container image built via GitHub Actions and pushed to Amazon ECR.
   * Auto-scaling based on average request latency (target < 400ms) and CPU utilization (> 70%).
2. **Amazon Bedrock**:
   * `anthropic.claude-3-5-sonnet-20241022-v2:0` for high-complexity agentic reasoning, cross-document comparison, and factual verification.
   * `amazon.titan-embed-text-v2:0` for generating 1024-dim dense embeddings.
3. **Amazon RDS PostgreSQL (with pgvector)**:
   * Replaces SQLite in production for high concurrency, ACID transactions, and indexed vector cosine queries.
4. **Amazon S3**:
   * Secure, versioned bucket with SSE-KMS encryption and lifecycle policies.
5. **AWS Secrets Manager & IAM Roles**:
   * Zero hard-coded credentials. The ECS Task Execution Role inherits least-privilege IAM policies to access Bedrock and S3.

---

## 3. Environment Variable Configuration

| Variable | Default Value | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `staging`, `production`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./nexus.db` | SQLAlchemy async connection string |
| `SECRET_KEY` | `nexus-dev-secret-key-change-in-production` | Secret key for JWT signing (HS256) |
| `AWS_BEDROCK_ENABLED` | `False` | Toggle AWS Bedrock integration (set to `True` in AWS) |
| `AWS_REGION` | `us-east-1` | Target AWS region for Bedrock & S3 |
| `BEDROCK_LLM_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Foundation model ID in Bedrock |
| `BEDROCK_EMBED_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Embedding model ID in Bedrock |
| `S3_BUCKET_NAME` | `nexus-enterprise-documents` | S3 bucket for PDF storage in production |
| `QDRANT_IN_MEMORY` | `True` | In-memory Qdrant engine toggle for local testing |
