from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.db.models import User, AuditLog
from backend.app.auth.rbac import get_current_user
from backend.app.agents.router import AgentRouter

router = APIRouter(prefix="/chat", tags=["Agentic RAG Chat"])
agent_router = AgentRouter()


class ChatRequestSchema(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class CitationSchema(BaseModel):
    document_name: str
    version: Optional[str] = None
    page: int
    section: Optional[str] = None
    excerpt: str


class AgentStepSchema(BaseModel):
    step: str
    classified_intent: Optional[str] = None
    mode: Optional[str] = None
    top_k: Optional[int] = None
    retrieved_chunks: Optional[int] = None
    grounding_score: Optional[float] = None
    model: Optional[str] = None


class MetricsSchema(BaseModel):
    latency_ms: int
    tokens: int
    cost_usd: float


class ChatResponseSchema(BaseModel):
    answer: str
    grounding_score: float
    verification_status: str
    citations: List[CitationSchema]
    agent_trace: List[Dict[str, Any]]
    metrics: MetricsSchema


@router.post("", response_model=ChatResponseSchema)
@router.post("/completions", response_model=ChatResponseSchema)
async def ask_agent(
    payload: ChatRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Chat message cannot be empty.")

    try:
        agent_res = await agent_router.execute_agent_workflow(
            db=db,
            user=current_user,
            query=payload.message
        )

        # Record Audit Log
        audit = AuditLog(
            user_id=current_user.id,
            query_text=payload.message,
            intent_classified=agent_res["agent_trace"][0].get("classified_intent"),
            retrieval_mode="hybrid_rerank",
            model_used="claude-3-5-sonnet",
            total_tokens=agent_res["metrics"]["tokens"],
            latency_ms=agent_res["metrics"]["latency_ms"],
            estimated_cost=agent_res["metrics"]["cost_usd"],
            grounding_score=agent_res["grounding_score"]
        )
        db.add(audit)
        await db.commit()

        return ChatResponseSchema(
            answer=agent_res["answer"],
            grounding_score=agent_res["grounding_score"],
            verification_status=agent_res["verification_status"],
            citations=[
                CitationSchema(
                    document_name=c["document_name"],
                    version=c.get("version"),
                    page=c["page"],
                    section=c.get("section"),
                    excerpt=c.get("excerpt", "")
                )
                for c in agent_res["citations"]
            ],
            agent_trace=agent_res["agent_trace"],
            metrics=MetricsSchema(
                latency_ms=agent_res["metrics"]["latency_ms"],
                tokens=agent_res["metrics"]["tokens"],
                cost_usd=agent_res["metrics"]["cost_usd"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow execution error: {str(e)}")


@router.post("/stream")
async def ask_agent_stream(
    payload: ChatRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Streams agent thought process, retrieval steps, answer tokens, and verified citations
    using Server-Sent Events (SSE).
    """
    import json
    import asyncio
    from fastapi.responses import StreamingResponse

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Chat message cannot be empty.")

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'query': payload.message})}\n\n"

            agent_res = await agent_router.execute_agent_workflow(
                db=db,
                user=current_user,
                query=payload.message
            )

            # Stream steps
            for step in agent_res.get("agent_trace", []):
                yield f"data: {json.dumps({'type': 'step', 'step': step.get('step'), 'details': step})}\n\n"
                await asyncio.sleep(0.04)

            # Stream tokens
            words = agent_res["answer"].split(" ")
            for w in words:
                yield f"data: {json.dumps({'type': 'token', 'token': w + ' '})}\n\n"
                await asyncio.sleep(0.015)

            # Record audit log
            audit = AuditLog(
                user_id=current_user.id,
                query_text=payload.message,
                intent_classified=agent_res.get("agent_trace", [{}])[0].get("classified_intent"),
                retrieval_mode="hybrid_rerank",
                model_used="claude-3-5-sonnet",
                total_tokens=agent_res["metrics"].get("tokens", 400),
                latency_ms=agent_res["metrics"].get("latency_ms", 100),
                estimated_cost=agent_res["metrics"].get("cost_usd", 0.0012),
                grounding_score=agent_res.get("grounding_score", 0.95)
            )
            db.add(audit)
            await db.commit()

            # Completion event
            yield f"data: {json.dumps({'type': 'done', 'citations': agent_res['citations'], 'grounding_score': agent_res['grounding_score'], 'metrics': agent_res['metrics'], 'full_answer': agent_res['answer']})}\n\n"

        except Exception as err:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(err)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
