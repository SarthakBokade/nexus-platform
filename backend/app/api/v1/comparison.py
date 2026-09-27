from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.db.models import User
from backend.app.auth.rbac import get_current_user
from backend.app.tools.comparison_tools import compare_documents, detect_conflicts

router = APIRouter(prefix="/compare", tags=["Document Comparison"])


class CompareRequestSchema(BaseModel):
    doc_id_1: str
    doc_id_2: str


class ConflictRequestSchema(BaseModel):
    topic: str


@router.post("")
async def compare_two_documents(
    payload: CompareRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        res = await compare_documents(db, current_user, payload.doc_id_1, payload.doc_id_2)
        if "error" in res:
            raise HTTPException(status_code=400, detail=res["error"])
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/conflicts")
async def detect_topic_conflicts(
    payload: ConflictRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await detect_conflicts(db, current_user, payload.topic)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conflict detection failed: {str(e)}")
