import os
import re
from typing import List, Dict, Any, Optional
import pypdf

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pymupdf as fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz
        HAS_PYMUPDF = True
    except ImportError:
        HAS_PYMUPDF = False


class ParsedPage:
    def __init__(self, page_number: int, text: str, tables: List[str] = None, sections: List[str] = None):
        self.page_number = page_number
        self.text = text
        self.tables = tables or []
        self.sections = sections or []


class PDFParser:
    """
    Page-aware and Section-aware PDF Parser.
    Extracts text, preserves section headers, and formats embedded tables into Markdown.
    """

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> List[ParsedPage]:
        parsed_pages: List[ParsedPage] = []

        if HAS_PYMUPDF:
            parsed_pages = PDFParser._parse_with_pymupdf(file_path)
        elif HAS_PDFPLUMBER:
            parsed_pages = PDFParser._parse_with_pdfplumber(file_path)
        else:
            parsed_pages = PDFParser._parse_with_pypdf(file_path)

        return parsed_pages

    @staticmethod
    def _parse_with_pymupdf(file_path: str) -> List[ParsedPage]:
        parsed_pages = []
        doc = fitz.open(file_path)

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_number = page_idx + 1
            raw_text = page.get_text("text")

            # Extract tables if available in PyMuPDF
            tables_md = []
            try:
                tabs = page.find_tables()
                if tabs:
                    for tab in tabs:
                        df = tab.extract()
                        if df and len(df) > 1:
                            headers = df[0]
                            rows = df[1:]
                            # Format Markdown Table
                            header_line = "| " + " | ".join(str(h or '').strip() for h in headers) + " |"
                            sep_line = "| " + " | ".join("---" for _ in headers) + " |"
                            row_lines = ["| " + " | ".join(str(cell or '').strip() for cell in row) + " |" for row in rows]
                            tables_md.append("\n".join([header_line, sep_line] + row_lines))
            except Exception:
                pass

            sections = PDFParser._detect_sections(raw_text)
            parsed_pages.append(ParsedPage(
                page_number=page_number,
                text=raw_text.strip(),
                tables=tables_md,
                sections=sections
            ))

        doc.close()
        return parsed_pages

    @staticmethod
    def _parse_with_pdfplumber(file_path: str) -> List[ParsedPage]:
        parsed_pages = []
        with pdfplumber.open(file_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_number = page_idx + 1
                raw_text = page.extract_text() or ""
                
                tables_md = []
                try:
                    tables = page.extract_tables()
                    for tab in tables:
                        if tab and len(tab) > 1:
                            headers = tab[0]
                            rows = tab[1:]
                            header_line = "| " + " | ".join(str(h or '').strip() for h in headers) + " |"
                            sep_line = "| " + " | ".join("---" for _ in headers) + " |"
                            row_lines = ["| " + " | ".join(str(cell or '').strip() for cell in row) + " |" for row in rows]
                            tables_md.append("\n".join([header_line, sep_line] + row_lines))
                except Exception:
                    pass

                sections = PDFParser._detect_sections(raw_text)
                parsed_pages.append(ParsedPage(
                    page_number=page_number,
                    text=raw_text.strip(),
                    tables=tables_md,
                    sections=sections
                ))
        return parsed_pages

    @staticmethod
    def _parse_with_pypdf(file_path: str) -> List[ParsedPage]:
        parsed_pages = []
        reader = pypdf.PdfReader(file_path)
        for page_idx, page in enumerate(reader.pages):
            page_number = page_idx + 1
            raw_text = page.extract_text() or ""
            sections = PDFParser._detect_sections(raw_text)
            parsed_pages.append(ParsedPage(
                page_number=page_number,
                text=raw_text.strip(),
                tables=[],
                sections=sections
            ))
        return parsed_pages

    @staticmethod
    def _detect_sections(text: str) -> List[str]:
        """
        Regex heuristic to detect section headings (e.g., '1. Introduction', 'Section 4.2', 'POLICY STATEMENT').
        """
        section_patterns = [
            r"^(?:Section\s+\d+(?:\.\d+)*|\d+(?:\.\d+)*)\s+[-—–:]?\s*([A-Z0-9\s,–—\-]{3,80})$",
            r"^([A-Z0-9\s,–—\-]{4,60})$"
        ]
        
        sections = []
        lines = text.split("\n")
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            for pattern in section_patterns:
                if re.match(pattern, line_clean):
                    if len(line_clean) < 80 and not line_clean.endswith("."):
                        sections.append(line_clean)
                        break
        return sections[:5] # Top 5 headers per page
