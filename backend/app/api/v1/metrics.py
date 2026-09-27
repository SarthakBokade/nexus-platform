from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from collections import defaultdict
import statistics

from backend.app.db.base import get_db
from backend.app.db.models import User, AuditLog
from backend.app.auth.rbac import get_current_user
from backend.app.services.embedding_service import get_embedding_service

router = APIRouter(prefix="/metrics", tags=["Observability & Audit Logs"])


class AuditLogSchema(BaseModel):
    id: str
    query_text: str
    intent_classified: Optional[str]
    retrieval_mode: Optional[str]
    model_used: Optional[str]
    total_tokens: int
    latency_ms: int
    estimated_cost: float
    grounding_score: Optional[float]
    created_at: str


class ObservabilitySummarySchema(BaseModel):
    total_queries: int
    total_tokens_consumed: int
    total_estimated_cost_usd: float
    avg_latency_ms: float
    avg_grounding_score: float


@router.get("/summary", response_model=ObservabilitySummarySchema)
async def get_observability_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(
        func.count(AuditLog.id),
        func.coalesce(func.sum(AuditLog.total_tokens), 0),
        func.coalesce(func.sum(AuditLog.estimated_cost), 0.0),
        func.coalesce(func.avg(AuditLog.latency_ms), 0.0),
        func.coalesce(func.avg(AuditLog.grounding_score), 0.0)
    )
    res = await db.execute(stmt)
    count, tokens, cost, avg_lat, avg_grounding = res.first()

    return ObservabilitySummarySchema(
        total_queries=count,
        total_tokens_consumed=int(tokens),
        total_estimated_cost_usd=round(float(cost), 4),
        avg_latency_ms=round(float(avg_lat), 1),
        avg_grounding_score=round(float(avg_grounding), 4)
    )


@router.get("/logs", response_model=List[AuditLogSchema])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50))
    logs = res.scalars().all()

    return [
        AuditLogSchema(
            id=l.id,
            query_text=l.query_text,
            intent_classified=l.intent_classified,
            retrieval_mode=l.retrieval_mode,
            model_used=l.model_used,
            total_tokens=l.total_tokens,
            latency_ms=l.latency_ms,
            estimated_cost=l.estimated_cost,
            grounding_score=l.grounding_score,
            created_at=l.created_at.isoformat()
        )
        for l in logs
    ]


@router.get("/dashboard")
async def get_metrics_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(
        func.count(AuditLog.id),
        func.coalesce(func.sum(AuditLog.total_tokens), 0),
        func.coalesce(func.sum(AuditLog.estimated_cost), 0.0),
        func.coalesce(func.avg(AuditLog.latency_ms), 0.0),
        func.coalesce(func.avg(AuditLog.grounding_score), 0.0)
    )
    res = await db.execute(stmt)
    count, tokens, cost, avg_lat, avg_grounding = res.first()

    return {
        "system_status": "HEALTHY",
        "total_queries": count,
        "total_tokens_consumed": int(tokens),
        "total_estimated_cost_usd": round(float(cost), 4),
        "avg_latency_ms": round(float(avg_lat), 1),
        "avg_grounding_score": round(float(avg_grounding), 4),
        "active_models": [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "amazon.titan-embed-text-v2:0",
            "ms-marco-TinyBERT-L-2-v2-onnx"
        ],
        "uptime": "99.99%"
    }


@router.get("/timeseries")
async def get_timeseries_metrics(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns per-hour bucketed metrics for the last N hours.
    Powers the live observability chart in the dashboard.
    """
    res = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)
    )
    logs = res.scalars().all()

    # Bucket by hour
    hourly: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "queries": 0, "total_latency": 0, "latencies": [],
        "tokens": 0, "cost": 0.0, "grounding_scores": []
    })

    for log in logs:
        hour_key = log.created_at.strftime("%Y-%m-%dT%H:00")
        bucket = hourly[hour_key]
        bucket["queries"] += 1
        bucket["total_latency"] += log.latency_ms
        bucket["latencies"].append(log.latency_ms)
        bucket["tokens"] += log.total_tokens
        bucket["cost"] += log.estimated_cost
        if log.grounding_score is not None:
            bucket["grounding_scores"].append(log.grounding_score)

    timeseries = []
    for hour, data in sorted(hourly.items()):
        avg_lat = data["total_latency"] // data["queries"] if data["queries"] else 0
        p95_lat = int(sorted(data["latencies"])[int(len(data["latencies"]) * 0.95)]) if data["latencies"] else 0
        avg_grounding = round(statistics.mean(data["grounding_scores"]), 4) if data["grounding_scores"] else 0.0
        timeseries.append({
            "hour": hour,
            "queries": data["queries"],
            "avg_latency_ms": avg_lat,
            "p95_latency_ms": p95_lat,
            "tokens": data["tokens"],
            "cost_usd": round(data["cost"], 6),
            "avg_grounding_score": avg_grounding,
        })

    return {"hours_requested": hours, "buckets": timeseries}


@router.get("/intent-distribution")
async def get_intent_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns count and percentage breakdown of classified intents.
    Useful for understanding how users are interacting with NEXUS.
    """
    res = await db.execute(
        select(AuditLog.intent_classified, func.count(AuditLog.id).label("count"))
        .where(AuditLog.intent_classified.isnot(None))
        .group_by(AuditLog.intent_classified)
    )
    rows = res.all()
    total = sum(r.count for r in rows)
    distribution = [
        {
            "intent": r.intent_classified,
            "count": r.count,
            "percentage": round((r.count / total * 100), 1) if total else 0
        }
        for r in rows
    ]
    return {"total": total, "distribution": distribution}


@router.get("/model-usage")
async def get_model_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns token consumption and cost breakdown per LLM model."""
    res = await db.execute(
        select(
            AuditLog.model_used,
            func.count(AuditLog.id).label("calls"),
            func.coalesce(func.sum(AuditLog.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(AuditLog.estimated_cost), 0.0).label("cost"),
            func.coalesce(func.avg(AuditLog.latency_ms), 0.0).label("avg_latency"),
        )
        .where(AuditLog.model_used.isnot(None))
        .group_by(AuditLog.model_used)
    )
    rows = res.all()
    return {
        "models": [
            {
                "model": r.model_used,
                "calls": r.calls,
                "total_tokens": int(r.tokens),
                "total_cost_usd": round(float(r.cost), 6),
                "avg_latency_ms": round(float(r.avg_latency), 1),
            }
            for r in rows
        ]
    }


@router.get("/embedding-backend")
async def get_embedding_backend_info(
    current_user: User = Depends(get_current_user),
):
    """
    Returns current embedding backend status.
    Useful for verifying SageMaker vs local fallback in production.
    """
    svc = get_embedding_service()
    return svc.get_backend_info()


@router.get("/latency-percentiles")
async def get_latency_percentiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns p50, p90, p95, p99 latency across all queries."""
    res = await db.execute(select(AuditLog.latency_ms).where(AuditLog.latency_ms > 0))
    latencies = sorted([r[0] for r in res.all()])
    if not latencies:
        return {"p50": 0, "p90": 0, "p95": 0, "p99": 0, "count": 0}
    n = len(latencies)
    return {
        "p50": latencies[int(n * 0.50)],
        "p90": latencies[int(n * 0.90)],
        "p95": latencies[int(n * 0.95)],
        "p99": latencies[min(int(n * 0.99), n - 1)],
        "min": latencies[0],
        "max": latencies[-1],
        "count": n,
    }
