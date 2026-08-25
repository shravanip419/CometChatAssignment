import re
from typing import List, Dict, Tuple
from pathlib import Path
from app.models.schemas import DocumentChunk, DocumentMetadata
from app.rag.loader import load_knowledge_base


def chunk_document(filename: str, metadata: DocumentMetadata, body: str) -> List[DocumentChunk]:
    """
    Chunks a document by headings (## Heading), preserving frontmatter metadata and heading paths.
    """
    chunks: List[DocumentChunk] = []
    
    # Split by markdown ## headings
    # Matches lines starting with ## 
    heading_pattern = re.compile(r"^(##\s+.+)$", re.MULTILINE)
    parts = heading_pattern.split(body)
    
    # Extract document title if present
    doc_title = metadata.title or filename
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if title_match:
        doc_title = title_match.group(1).strip()

    # If the first part has content before any ## heading
    preamble = parts[0].strip()
    # Remove # Main Title from preamble if present
    preamble = re.sub(r"^#\s+.+\n*", "", preamble).strip()
    if preamble:
        chunks.append(
            DocumentChunk(
                chunk_id=f"{filename}#overview",
                filename=filename,
                heading=f"{doc_title} - Overview",
                content=preamble,
                metadata=metadata,
            )
        )
    
    # Iterate through remaining (heading, content) pairs
    i = 1
    while i < len(parts):
        heading_line = parts[i].strip()
        heading_text = re.sub(r"^##\s*", "", heading_line).strip()
        content = parts[i + 1].strip() if (i + 1) < len(parts) else ""
        
        full_heading = f"{doc_title} - {heading_text}" if doc_title else heading_text
        slug = re.sub(r"[^a-zA-Z0-9_-]", "-", heading_text.lower())
        
        if content:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{filename}#{slug}",
                    filename=filename,
                    heading=heading_text,  # Clean section heading
                    content=content,
                    metadata=metadata,
                )
            )
        i += 2
        
    return chunks


def build_kb_chunks(kb_dir: Path) -> List[DocumentChunk]:
    """
    Loads all markdown documents from kb_dir and returns all chunks.
    """
    docs = load_knowledge_base(kb_dir)
    all_chunks: List[DocumentChunk] = []
    for filename, (meta, body) in docs.items():
        doc_chunks = chunk_document(filename, meta, body)
        all_chunks.extend(doc_chunks)
    return all_chunks
