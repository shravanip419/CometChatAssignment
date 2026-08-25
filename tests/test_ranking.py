import pytest
from app.rag.ranking import MetadataRanker
from app.models.schemas import DocumentChunk, DocumentMetadata


def test_ranking_excludes_superseded():
    ranker = MetadataRanker()
    
    active_chunk = DocumentChunk(
        chunk_id="active-1",
        filename="01-returns-policy-current.md",
        heading="Standard return",
        content="30 days return",
        metadata=DocumentMetadata(document_id="RET-2026-01", status="active", policy_authority="official")
    )
    superseded_chunk = DocumentChunk(
        chunk_id="legacy-1",
        filename="02-returns-policy-legacy.md",
        heading="Legacy return",
        content="45 days return",
        metadata=DocumentMetadata(document_id="RET-2024-01", status="superseded", policy_authority="official")
    )
    
    candidates = [(superseded_chunk, 0.9), (active_chunk, 0.85)]
    ranked = ranker.rank(candidates, allow_superseded=False)
    
    assert len(ranked) == 1
    assert ranked[0][0].chunk_id == "active-1"


def test_ranking_excludes_draft_and_none_authority():
    ranker = MetadataRanker()
    
    draft_chunk = DocumentChunk(
        chunk_id="draft-1",
        filename="14-internal-content-migration-notes.md",
        heading="Scratchpad",
        content="Draft notes",
        metadata=DocumentMetadata(document_id="MIG-01", status="draft", policy_authority="none", customer_answering=False)
    )
    official_chunk = DocumentChunk(
        chunk_id="off-1",
        filename="01-returns-policy-current.md",
        heading="Standard",
        content="Official policy",
        metadata=DocumentMetadata(document_id="RET-01", status="active", policy_authority="official")
    )
    
    candidates = [(draft_chunk, 0.99), (official_chunk, 0.7)]
    ranked = ranker.rank(candidates, allow_internal=False)
    
    assert len(ranked) == 1
    assert ranked[0][0].chunk_id == "off-1"
