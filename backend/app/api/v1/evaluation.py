from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.db.base import get_db
from backend.app.db.models import User, EvaluationRun
from backend.app.auth.rbac import get_current_user
from backend.app.evaluation.evaluator import BenchmarkEvaluator

router = APIRouter(prefix="/evaluation", tags=["ML Evaluation & Experiments"])
evaluator = BenchmarkEvaluator()


class RunBenchmarkSchema(BaseModel):
    strategy: str = "hybrid_rerank" # dense, bm25, hybrid, hybrid_rerank


class EvaluationRunSchema(BaseModel):
    id: str
    run_name: str
    retrieval_strategy: str
    recall_at_5: float
    precision_at_5: float
    mrr: float
    ndcg: float
    faithfulness_score: float
    citation_accuracy: float
    avg_latency_ms: int
    created_at: str
    model_config = ConfigDict(from_attributes=True)


@router.get("/runs", response_model=List[EvaluationRunSchema])
async def list_evaluation_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()))
    runs = res.scalars().all()
    return [
        EvaluationRunSchema(
            id=r.id,
            run_name=r.run_name,
            retrieval_strategy=r.retrieval_strategy,
            recall_at_5=r.recall_at_5,
            precision_at_5=r.precision_at_5,
            mrr=r.mrr,
            ndcg=r.ndcg,
            faithfulness_score=r.faithfulness_score,
            citation_accuracy=r.citation_accuracy,
            avg_latency_ms=r.avg_latency_ms,
            created_at=r.created_at.isoformat()
        )
        for r in runs
    ]


@router.post("/run", response_model=EvaluationRunSchema)
@router.post("/benchmark", response_model=EvaluationRunSchema)
@router.post("/run-benchmark", response_model=EvaluationRunSchema)
async def trigger_benchmark_run(
    payload: RunBenchmarkSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        run = await evaluator.run_benchmark_experiment(db, current_user, payload.strategy)
        return EvaluationRunSchema(
            id=run.id,
            run_name=run.run_name,
            retrieval_strategy=run.retrieval_strategy,
            recall_at_5=run.recall_at_5,
            precision_at_5=run.precision_at_5,
            mrr=run.mrr,
            ndcg=run.ndcg,
            faithfulness_score=run.faithfulness_score,
            citation_accuracy=run.citation_accuracy,
            avg_latency_ms=run.avg_latency_ms,
            created_at=run.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation experiment failed: {str(e)}")
