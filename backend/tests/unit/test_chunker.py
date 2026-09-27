import pytest
from backend.app.ingestion.parsers import ParsedPage
from backend.app.ingestion.chunker import SemanticChunker


def test_semantic_chunker_tables_and_sections():
    page1 = ParsedPage(
        page_number=1,
        text="Section 1. Travel Guidelines\nAll employees must follow hotel allowance caps.\n\nSection 2. Reimbursement Caps\nHotel allowance is 5000 per night.",
        tables=["| Category | Allowance |\n|---|---|\n| Hotel | 5000 |"],
        sections=["Section 1. Travel Guidelines", "Section 2. Reimbursement Caps"]
    )
    
    chunker = SemanticChunker(target_chunk_size=100, chunk_overlap=10)
    doc_metadata = {
        "document_id": "test-doc-123",
        "filename": "Test_Policy.pdf",
        "access_level": "Internal"
    }
    
    chunks = chunker.create_chunks([page1], doc_metadata)
    
    assert len(chunks) >= 2
    # Check table chunk
    table_chunk = next(c for c in chunks if c.metadata_json.get("is_table"))
    assert "Category" in table_chunk.content
    assert table_chunk.page_number == 1
    
    # Check section chunk metadata
    text_chunks = [c for c in chunks if not c.metadata_json.get("is_table")]
    assert len(text_chunks) > 0
    assert text_chunks[0].metadata_json["access_level"] == "Internal"
