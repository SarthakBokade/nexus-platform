import re
from typing import List, Dict, Any, Optional
from backend.app.ingestion.parsers import ParsedPage


class ChunkData:
    def __init__(
        self,
        chunk_index: int,
        page_number: int,
        section: Optional[str],
        subsection: Optional[str],
        content: str,
        token_count: int,
        metadata_json: Dict[str, Any]
    ):
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.section = section
        self.subsection = subsection
        self.content = content
        self.token_count = token_count
        self.metadata_json = metadata_json


class SemanticChunker:
    """
    Page-aware and Section-aware Chunking Engine.
    Splits text by structural sections, paragraphs, and tables without breaking table markdown.
    """

    def __init__(self, target_chunk_size: int = 400, chunk_overlap: int = 50):
        self.target_chunk_size = target_chunk_size # In words (~500 tokens)
        self.chunk_overlap = chunk_overlap

    def create_chunks(self, parsed_pages: List[ParsedPage], doc_metadata: Dict[str, Any]) -> List[ChunkData]:
        chunks: List[ChunkData] = []
        global_chunk_idx = 0

        for page in parsed_pages:
            page_num = page.page_number
            current_section = page.sections[0] if page.sections else "General"
            
            # 1. Process Embedded Tables as Standalone Chunks
            for tab_idx, table_md in enumerate(page.tables):
                chunk_meta = {
                    **doc_metadata,
                    "page_number": page_num,
                    "section": current_section,
                    "is_table": True
                }
                chunks.append(ChunkData(
                    chunk_index=global_chunk_idx,
                    page_number=page_num,
                    section=current_section,
                    subsection=f"Table {tab_idx + 1}",
                    content=f"### Table on Page {page_num} - {current_section}\n\n" + table_md,
                    token_count=len(table_md.split()),
                    metadata_json=chunk_meta
                ))
                global_chunk_idx += 1

            # 2. Process Page Text into Semantic Paragraph Batches
            text = page.text
            if not text:
                continue

            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
            
            current_buffer = []
            current_word_count = 0
            current_subsection = None

            for para in paragraphs:
                # Check if paragraph is a heading
                if len(para) < 80 and not para.endswith("."):
                    if current_buffer:
                        # Flush current buffer
                        chunk_text = "\n\n".join(current_buffer)
                        chunk_meta = {
                            **doc_metadata,
                            "page_number": page_num,
                            "section": current_section,
                            "subsection": current_subsection
                        }
                        chunks.append(ChunkData(
                            chunk_index=global_chunk_idx,
                            page_number=page_num,
                            section=current_section,
                            subsection=current_subsection,
                            content=chunk_text,
                            token_count=len(chunk_text.split()),
                            metadata_json=chunk_meta
                        ))
                        global_chunk_idx += 1
                        current_buffer = []
                        current_word_count = 0
                    
                    current_section = para
                    continue

                words = para.split()
                if current_word_count + len(words) > self.target_chunk_size and current_buffer:
                    # Flush chunk
                    chunk_text = "\n\n".join(current_buffer)
                    chunk_meta = {
                        **doc_metadata,
                        "page_number": page_num,
                        "section": current_section,
                        "subsection": current_subsection
                    }
                    chunks.append(ChunkData(
                        chunk_index=global_chunk_idx,
                        page_number=page_num,
                        section=current_section,
                        subsection=current_subsection,
                        content=chunk_text,
                        token_count=len(chunk_text.split()),
                        metadata_json=chunk_meta
                    ))
                    global_chunk_idx += 1
                    
                    # Maintain overlap
                    overlap_para = current_buffer[-1] if current_buffer else ""
                    current_buffer = [overlap_para, para] if overlap_para else [para]
                    current_word_count = len(overlap_para.split()) + len(words)
                else:
                    current_buffer.append(para)
                    current_word_count += len(words)

            # Flush remaining buffer for page
            if current_buffer:
                chunk_text = "\n\n".join(current_buffer)
                chunk_meta = {
                    **doc_metadata,
                    "page_number": page_num,
                    "section": current_section,
                    "subsection": current_subsection
                }
                chunks.append(ChunkData(
                    chunk_index=global_chunk_idx,
                    page_number=page_num,
                    section=current_section,
                    subsection=current_subsection,
                    content=chunk_text,
                    token_count=len(chunk_text.split()),
                    metadata_json=chunk_meta
                ))
                global_chunk_idx += 1

        return chunks
