import os
import psutil
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from backend.app.config import settings
from backend.app.db.base import get_db

router = APIRouter(prefix="/health", tags=["System Health"])
START_TIME = datetime.now(timezone.utc)


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    uptime_seconds = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    
    # Process Memory Utilization
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": int(uptime_seconds),
        "database": db_status,
        "memory_usage_mb": round(mem_info.rss / (1024 * 1024), 2),
        "aws_bedrock_enabled": settings.USE_AWS_BEDROCK,
        "qdrant_in_memory": settings.QDRANT_IN_MEMORY
    }
