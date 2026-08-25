import pytest
from app.rag.chunker import build_kb_chunks, chunk_document
from app.models.schemas import DocumentMetadata
from app.config import KNOWLEDGE_BASE_DIR


def test_build_kb_chunks_preserves_metadata():
    chunks = build_kb_chunks(KNOWLEDGE_BASE_DIR)
    assert len(chunks) > 20
    for chunk in chunks:
        assert chunk.chunk_id
        assert chunk.filename.endswith(".md")
        assert chunk.heading
        assert chunk.content
        assert chunk.metadata.document_id


def test_chunk_document_sections():
    meta = DocumentMetadata(document_id="DOC-1", title="Sample Doc", status="active")
    sample_body = """# Sample Doc

## Section One
First section content.

## Section Two
Second section content.
"""
    chunks = chunk_document("sample.md", meta, sample_body)
    assert len(chunks) == 2
    assert chunks[0].heading == "Section One"
    assert chunks[0].content == "First section content."
    assert chunks[1].heading == "Section Two"
    assert chunks[1].content == "Second section content."
