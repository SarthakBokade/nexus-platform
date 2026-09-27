import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="Employee", nullable=False) # Admin, Employee, HR, Finance, Security
    department: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[List["ConversationSession"]] = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    s3_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), default="Policy") # Policy, SOP, Financial, HR, Contract, Technical
    department: Mapped[str] = mapped_column(String(100), default="General", index=True)
    author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    effective_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # YYYY-MM-DD
    access_level: Mapped[str] = mapped_column(String(50), default="Internal", index=True) # Public, Internal, Restricted, Confidential
    superseded_by_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="processed") # processing, processed, error
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Self-referential relationship for superseded versioning
    superseded_by: Mapped[Optional["Document"]] = relationship("Document", remote_side=[id])
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subsection: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_level: Mapped[str] = mapped_column(String(50), default="Internal", index=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent_classified: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retrieval_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    grounding_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_name: Mapped[str] = mapped_column(String(100), nullable=False)
    retrieval_strategy: Mapped[str] = mapped_column(String(50), nullable=False) # Dense, Lexical, Hybrid, Hybrid+Rerank
    recall_at_5: Mapped[float] = mapped_column(Float, default=0.0)
    precision_at_5: Mapped[float] = mapped_column(Float, default=0.0)
    mrr: Mapped[float] = mapped_column(Float, default=0.0)
    ndcg: Mapped[float] = mapped_column(Float, default=0.0)
    faithfulness_score: Mapped[float] = mapped_column(Float, default=0.0)
    citation_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ConversationSession(Base):
    """Groups multi-turn messages into a named session per user."""
    __tablename__ = "conversation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="session", cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at"
    )


class ConversationMessage(Base):
    """Individual turn in a multi-turn conversation with full agent metadata."""
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent_classified: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grounding_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citations_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    agent_trace_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    session: Mapped["ConversationSession"] = relationship("ConversationSession", back_populates="messages")
