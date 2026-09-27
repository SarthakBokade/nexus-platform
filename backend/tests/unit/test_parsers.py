import os
import pytest
from backend.app.ingestion.parsers import PDFParser


def test_pdf_parser_real_document():
    pdf_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "sample_data",
        "documents",
        "Travel_Policy_2025.pdf"
    )
    assert os.path.exists(pdf_path), f"File {pdf_path} not found"

    parsed_pages = PDFParser.extract_text_from_pdf(pdf_path)
    assert len(parsed_pages) >= 1
    
    first_page = parsed_pages[0]
    assert first_page.page_number == 1
    assert len(first_page.text) > 50
    assert "travel" in first_page.text.lower()
    assert "reimbursement" in first_page.text.lower()
