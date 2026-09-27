import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.db.base import get_db
from backend.app.db.models import User, Document, DocumentChunk
from backend.app.auth.rbac import get_current_user, get_allowed_access_levels, check_document_access
from backend.app.ingestion.validator import validate_file
from backend.app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/documents", tags=["Document Management"])


class DocumentSchema(BaseModel):
    id: str
    filename: str
    document_type: str
    department: str
    author: Optional[str]
    version: str
    effective_date: Optional[str]
    access_level: str
    status: str
    page_count: int
    chunk_count: int
    summary: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class DocumentChunkSchema(BaseModel):
    id: str
    chunk_index: int
    page_number: int
    section: Optional[str]
    subsection: Optional[str]
    content: str
    token_count: int
    access_level: str


class DocumentDetailSchema(DocumentSchema):
    chunks: List[DocumentChunkSchema]


@router.post("/upload", response_model=DocumentSchema)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    effective_date: Optional[str] = Form(None),
    access_level: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    file_bytes = await file.read()
    
    # 1. Validate File
    is_valid, err_msg = validate_file(file, file_bytes)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    # 2. Metadata overrides
    user_metadata = {
        "document_type": document_type,
        "department": department,
        "version": version,
        "effective_date": effective_date,
        "access_level": access_level or "Internal",
        "author": current_user.full_name
    }

    try:
        doc, status_info = await IngestionPipeline.process_document(
            db=db,
            file_name=file.filename or "uploaded_document.pdf",
            file_bytes=file_bytes,
            user_metadata=user_metadata
        )
        return DocumentSchema(
            id=doc.id,
            filename=doc.filename,
            document_type=doc.document_type,
            department=doc.department,
            author=doc.author,
            version=doc.version,
            effective_date=doc.effective_date,
            access_level=doc.access_level,
            status=doc.status,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            summary=doc.summary,
            created_at=doc.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")


@router.get("", response_model=List[DocumentSchema])
async def list_documents(
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    allowed_access_levels = get_allowed_access_levels(current_user.role)
    
    query = select(Document).where(Document.access_level.in_(allowed_access_levels))
    if department:
        query = query.where(Document.department == department)
        
    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    docs = result.scalars().all()
    
    return [
        DocumentSchema(
            id=d.id,
            filename=d.filename,
            document_type=d.document_type,
            department=d.department,
            author=d.author,
            version=d.version,
            effective_date=d.effective_date,
            access_level=d.access_level,
            status=d.status,
            page_count=d.page_count,
            chunk_count=d.chunk_count,
            summary=d.summary,
            created_at=d.created_at.isoformat()
        )
        for d in docs
    ]


@router.get("/{doc_id}", response_model=DocumentDetailSchema)
async def get_document_by_id(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not check_document_access(current_user, doc.access_level, doc.department):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Your role '{current_user.role}' is not authorized to view document '{doc.filename}' with access level '{doc.access_level}'."
        )

    chunks_res = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index))
    chunks = chunks_res.scalars().all()

    return DocumentDetailSchema(
        id=doc.id,
        filename=doc.filename,
        document_type=doc.document_type,
        department=doc.department,
        author=doc.author,
        version=doc.version,
        effective_date=doc.effective_date,
        access_level=doc.access_level,
        status=doc.status,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        summary=doc.summary,
        created_at=doc.created_at.isoformat(),
        chunks=[
            DocumentChunkSchema(
                id=c.id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                section=c.section,
                subsection=c.subsection,
                content=c.content,
                token_count=c.token_count,
                access_level=c.access_level
            )
            for c in chunks
        ]
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["Admin", "Security"]:
        raise HTTPException(status_code=403, detail="Only Admin or Security roles can delete documents.")

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()
    return {"message": f"Document '{doc.filename}' deleted successfully."}
