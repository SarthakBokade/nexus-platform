import os
import sys
import asyncio
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.future import select
from backend.app.db.base import AsyncSessionLocal, engine
from backend.app.db.models import User, EvaluationRun
from backend.app.evaluation.evaluator import BenchmarkEvaluator


async def run_all_benchmarks():
    print("=" * 70)
    print("NEXUS — Executing ML Retrieval & Generation Benchmark Experiments")
    print("=" * 70)

    evaluator = BenchmarkEvaluator()
    strategies = ["dense", "bm25", "hybrid", "hybrid_rerank"]

    async with AsyncSessionLocal() as session:
        admin_res = await session.execute(select(User).where(User.email == "admin@nexus.com"))
        admin = admin_res.scalars().first()
        if not admin:
            print("[-] Admin user not found! Please run seed_and_demo.py first.")
            return

        for strat in strategies:
            print(f"\n[*] Running Benchmark for Strategy: '{strat}'...")
            run = await evaluator.run_benchmark_experiment(session, admin, strategy=strat)
            print(f"    - Recall@5:      {run.recall_at_5:.4f}")
            print(f"    - Precision@5:   {run.precision_at_5:.4f}")
            print(f"    - MRR:           {run.mrr:.4f}")
            print(f"    - NDCG@5:        {run.ndcg:.4f}")
            print(f"    - Faithfulness:  {run.faithfulness_score:.4f}")
            print(f"    - Avg Latency:   {run.avg_latency_ms} ms")

        # Summary Table
        print("\n" + "=" * 70)
        print("EXPERIMENT COMPARISON SUMMARY")
        print("=" * 70)
        runs_res = await session.execute(select(EvaluationRun).order_by(EvaluationRun.created_at))
        runs = runs_res.scalars().all()
        print(f"{'Strategy':<18} | {'Recall@5':<10} | {'MRR':<8} | {'NDCG@5':<8} | {'Faithfulness':<12} | {'Latency':<8}")
        print("-" * 75)
        for r in runs:
            print(f"{r.retrieval_strategy:<18} | {r.recall_at_5:<10.4f} | {r.mrr:<8.4f} | {r.ndcg:<8.4f} | {r.faithfulness_score:<12.4f} | {r.avg_latency_ms} ms")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
