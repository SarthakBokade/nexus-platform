"""
Conversations API — Phase 3: Multi-Turn Memory Endpoints

Routes:
  POST   /conversations                        — Create new session
  GET    /conversations                        — List user's sessions
  GET    /conversations/{session_id}           — Get session + full message history
  DELETE /conversations/{session_id}           — Delete session
  POST   /conversations/{session_id}/messages  — Send message (memory-aware)
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.db.models import User, AuditLog
from backend.app.auth.rbac import get_current_user
from backend.app.agents.router import AgentRouter
from backend.app.services.memory_service import ConversationMemoryService

router = APIRouter(prefix="/conversations", tags=["Conversation Memory"])

agent_router = AgentRouter()
memory_service = ConversationMemoryService()


# ------------------------------------------------------------------ #
# Schemas                                                              #
# ------------------------------------------------------------------ #

class CreateSessionSchema(BaseModel):
    title: Optional[str] = None


class SessionSchema(BaseModel):
    id: str
    title: str
    turn_count: int
    created_at: str
    updated_at: str


class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    intent_classified: Optional[str] = None
    grounding_score: Optional[float] = None
    citations: Optional[List[Dict[str, Any]]] = None
    tokens_used: int = 0
    latency_ms: int = 0
    created_at: str


class SessionDetailSchema(BaseModel):
    id: str
    title: str
    turn_count: int
    messages: List[MessageSchema]
    created_at: str
    updated_at: str


class SendMessageSchema(BaseModel):
    message: str
    use_memory: bool = True  # If False, ignores history (stateless mode)


class SendMessageResponseSchema(BaseModel):
    session_id: str
    answer: str
    grounding_score: float
    verification_status: str
    citations: List[Dict[str, Any]]
    agent_trace: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    history_turns_used: int


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@router.post("", response_model=SessionSchema)
async def create_session(
    payload: CreateSessionSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new conversation session for the authenticated user."""
    session = await memory_service.create_session(db, current_user.id, payload.title)
    return SessionSchema(
        id=session.id,
        title=session.title,
        turn_count=session.turn_count,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.get("", response_model=List[SessionSchema])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all conversation sessions for the current user, newest first."""
    sessions = await memory_service.list_sessions(db, current_user.id)
    return [
        SessionSchema(
            id=s.id,
            title=s.title,
            turn_count=s.turn_count,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionDetailSchema)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns a session with full message history."""
    session = await memory_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation session not found.")

    messages = await memory_service.get_messages(db, session_id)
    return SessionDetailSchema(
        id=session.id,
        title=session.title,
        turn_count=session.turn_count,
        messages=[
            MessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                intent_classified=m.intent_classified,
                grounding_score=m.grounding_score,
                citations=m.citations_json or [],
                tokens_used=m.tokens_used,
                latency_ms=m.latency_ms,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes a conversation session and all its messages."""
    deleted = await memory_service.delete_session(db, session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": True, "session_id": session_id}


@router.post("/{session_id}/messages", response_model=SendMessageResponseSchema)
async def send_message(
    session_id: str,
    payload: SendMessageSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sends a user message within an existing session.
    Builds a multi-turn context window and injects conversation history
    into the agent's query before running the full agentic workflow.
    """
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Verify session ownership
    session = await memory_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Persist user turn
    await memory_service.add_user_message(db, session_id, payload.message)

    # Build context-aware query
    history_context = ""
    history_turns_used = 0
    if payload.use_memory:
        history_context = await memory_service.build_context_window(
            db, session_id, payload.message
        )
        if history_context:
            history_turns_used = history_context.count("[Turn ")

    # Augment query with conversation history
    augmented_query = payload.message
    if history_context:
        augmented_query = (
            f"[Conversation History]\n{history_context}\n\n"
            f"[Current Question]\n{payload.message}"
        )

    # Run agent workflow
    try:
        agent_res = await agent_router.execute_agent_workflow(
            db=db,
            user=current_user,
            query=augmented_query,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Persist assistant turn
    await memory_service.add_assistant_message(
        db=db,
        session_id=session_id,
        content=agent_res["answer"],
        intent_classified=agent_res["agent_trace"][0].get("classified_intent") if agent_res["agent_trace"] else None,
        grounding_score=agent_res["grounding_score"],
        citations=agent_res["citations"],
        agent_trace=agent_res["agent_trace"],
        tokens_used=agent_res["metrics"].get("tokens", 0),
        latency_ms=agent_res["metrics"].get("latency_ms", 0),
    )

    # Record audit log
    audit = AuditLog(
        user_id=current_user.id,
        query_text=payload.message,
        intent_classified=agent_res["agent_trace"][0].get("classified_intent") if agent_res["agent_trace"] else None,
        retrieval_mode="hybrid_rerank",
        model_used=agent_res["metrics"].get("model_used", "claude-3-5-sonnet"),
        total_tokens=agent_res["metrics"].get("tokens", 0),
        latency_ms=agent_res["metrics"].get("latency_ms", 0),
        estimated_cost=agent_res["metrics"].get("cost_usd", 0.0),
        grounding_score=agent_res["grounding_score"],
    )
    db.add(audit)
    await db.commit()

    return SendMessageResponseSchema(
        session_id=session_id,
        answer=agent_res["answer"],
        grounding_score=agent_res["grounding_score"],
        verification_status=agent_res["verification_status"],
        citations=agent_res["citations"],
        agent_trace=agent_res["agent_trace"],
        metrics=agent_res["metrics"],
        history_turns_used=history_turns_used,
    )
