import pytest
from pathlib import Path
from app.rag.loader import load_knowledge_base, parse_frontmatter
from app.rag.chunker import build_kb_chunks, chunk_document
from app.rag.retriever import KnowledgeRetriever
from app.config import KNOWLEDGE_BASE_DIR


def test_frontmatter_parsing():
    sample_md = """---
document_id: TEST-01
title: Test Title
status: active
audience: customer
policy_authority: official
supersedes: OLD-01
---

# Test Title

## Section 1
This is section 1.
"""
    meta, body = parse_frontmatter(sample_md)
    assert meta.document_id == "TEST-01"
    assert meta.title == "Test Title"
    assert meta.status == "active"
    assert meta.supersedes == "OLD-01"
    assert "## Section 1" in body


def test_chunking_preserves_metadata():
    chunks = build_kb_chunks(KNOWLEDGE_BASE_DIR)
    assert len(chunks) > 0
    # Verify all chunks have required fields
    for chunk in chunks:
        assert chunk.filename.endswith(".md")
        assert chunk.heading
        assert chunk.content
        assert chunk.metadata.document_id


def test_retriever_superseded_filtering():
    retriever = KnowledgeRetriever()
    results = retriever.retrieve("How long do I have to return an item?")
    assert len(results) > 0
    
    # 01-returns-policy-current.md must be retrieved, NOT 02-returns-policy-legacy.md
    filenames = [c.filename for c, _ in results]
    assert "01-returns-policy-current.md" in filenames
    assert "02-returns-policy-legacy.md" not in filenames


def test_retriever_scratchpad_exclusion():
    retriever = KnowledgeRetriever()
    results = retriever.retrieve("What does the migration note say about returns?")
    filenames = [c.filename for c, _ in results]
    # Migration notes must NOT be included as authoritative customer policy
    assert "14-internal-content-migration-notes.md" not in filenames


def test_retriever_trailplus_policy():
    retriever = KnowledgeRetriever()
    results = retriever.retrieve("My TrailPlus membership was active when I ordered. What is my return window?")
    filenames = [c.filename for c, _ in results]
    assert "09-trailplus-membership.md" in filenames


def test_retriever_breeze_tumbler_conflict_sources():
    retriever = KnowledgeRetriever()
    results = retriever.retrieve("Can I put the entire Breeze Tumbler in the dishwasher?")
    filenames = [c.filename for c, _ in results]
    assert "11-product-care.md" in filenames
    assert "12-breeze-tumbler-product-card.md" in filenames


def test_retriever_damaged_final_sale_sources():
    retriever = KnowledgeRetriever()
    results = retriever.retrieve("A final-sale bag arrived with a broken zipper yesterday. Am I completely out of luck?")
    filenames = [c.filename for c, _ in results]
    assert "03-final-sale-and-promotions.md" in filenames
    assert "04-damaged-or-wrong-items.md" in filenames
