import os
import logging
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.config import settings
from backend.app.db.models import Document, DocumentChunk
from backend.app.ingestion.validator import validate_file, compute_file_hash, scan_for_prompt_injection
from backend.app.ingestion.parsers import PDFParser
from backend.app.ingestion.metadata import extract_metadata_from_filename_and_text
from backend.app.ingestion.chunker import SemanticChunker

logger = logging.getLogger("nexus.ingestion")


class IngestionPipeline:

    @staticmethod
    async def process_document(
        db: AsyncSession,
        file_name: str,
        file_bytes: bytes,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Document, Dict[str, Any]]:
        """
        Executes end-to-end document ingestion pipeline:
        Validation -> Deduplication -> Saving -> Page Parsing -> Metadata Extraction -> Semantic Chunking -> DB Storage
        """
        # 1. Compute Hash for Deduplication
        file_hash = compute_file_hash(file_bytes)
        existing_doc_res = await db.execute(select(Document).where(Document.file_hash == file_hash))
        existing_doc = existing_doc_res.scalars().first()
        if existing_doc:
            logger.info(f"Duplicate document uploaded (Hash: {file_hash[:8]}). Returning existing record.")
            return existing_doc, {"is_duplicate": True, "message": "Document already ingested."}

        # 2. Save File locally to Storage
        target_path = os.path.join(settings.STORAGE_DIR, f"{file_hash[:12]}_{file_name}")
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        # 3. Parse Page-by-Page
        if file_name.lower().endswith(".pdf"):
            parsed_pages = PDFParser.extract_text_from_pdf(target_path)
        else:
            # Simple text/markdown fallback
            raw_text = file_bytes.decode("utf-8", errors="ignore")
            from backend.app.ingestion.parsers import ParsedPage
            parsed_pages = [ParsedPage(page_number=1, text=raw_text)]

        if not parsed_pages or not any(p.text for p in parsed_pages):
            raise ValueError("Failed to extract readable text from uploaded document.")

        first_page_text = parsed_pages[0].text if parsed_pages else ""

        # 4. Prompt Injection Scan
        all_text = "\n".join(p.text for p in parsed_pages)
        injection_threats = scan_for_prompt_injection(all_text)
        if injection_threats:
            logger.warning(f"Document '{file_name}' contains prompt injection threat patterns: {injection_threats}")

        # 5. Metadata Auto-Extraction
        extracted_meta = extract_metadata_from_filename_and_text(file_name, first_page_text, user_metadata)

        # 6. Database Document Record Creation
        doc = Document(
            filename=file_name,
            file_path=target_path,
            file_hash=file_hash,
            document_type=extracted_meta["document_type"],
            department=extracted_meta["department"],
            author=extracted_meta["author"],
            version=extracted_meta["version"],
            effective_date=extracted_meta["effective_date"],
            access_level=extracted_meta["access_level"],
            status="processed",
            page_count=len(parsed_pages),
            summary=first_page_text[:300] + "..." if len(first_page_text) > 300 else first_page_text
        )
        db.add(doc)
        await db.flush() # Generate doc.id

        # 7. Semantic Chunking
        chunker = SemanticChunker(target_chunk_size=350, chunk_overlap=40)
        chunk_data_list = chunker.create_chunks(parsed_pages, doc_metadata={
            "document_id": doc.id,
            "filename": doc.filename,
            "department": doc.department,
            "access_level": doc.access_level,
            "version": doc.version
        })

        # 8. Create DB Chunk Records
        db_chunks = []
        for cd in chunk_data_list:
            chunk_rec = DocumentChunk(
                document_id=doc.id,
                chunk_index=cd.chunk_index,
                page_number=cd.page_number,
                section=cd.section,
                subsection=cd.subsection,
                content=cd.content,
                token_count=cd.token_count,
                access_level=doc.access_level,
                metadata_json=cd.metadata_json
            )
            db.add(chunk_rec)
            db_chunks.append(chunk_rec)

        doc.chunk_count = len(db_chunks)
        await db.commit()
        await db.refresh(doc)

        # 9. Index Chunks into Qdrant Vector Engine
        try:
            from backend.app.retrieval.dense import DenseRetriever
            dense_retriever = DenseRetriever()
            vector_items = []
            for cr in db_chunks:
                vec = dense_retriever.embed_text(cr.content)
                vector_items.append({
                    "chunk_id": cr.id,
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "version": doc.version,
                    "department": doc.department,
                    "access_level": doc.access_level,
                    "page_number": cr.page_number,
                    "section": cr.section,
                    "content": cr.content,
                    "vector": vec
                })
            dense_retriever.qdrant.upsert_chunks(vector_items)
        except Exception as e:
            logger.warning(f"Could not index chunks to Qdrant during ingestion: {e}")

        logger.info(f"Successfully processed '{file_name}' -> {len(db_chunks)} chunks across {len(parsed_pages)} pages.")
        return doc, {
            "is_duplicate": False,
            "prompt_injection_threats": injection_threats,
            "chunks_created": len(db_chunks)
        }
