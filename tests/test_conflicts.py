import pytest
from app.rag.conflict_detector import ConflictDetector
from app.models.schemas import DocumentChunk, DocumentMetadata


def test_conflict_detector_identifies_care_contradiction():
    detector = ConflictDetector()
    
    chunk_a = DocumentChunk(
        chunk_id="care-tumbler",
        filename="11-product-care.md",
        heading="Breeze Tumbler",
        content="The stainless-steel body of the Breeze Tumbler should be hand-washed. The lid may be placed on the top rack.",
        metadata=DocumentMetadata(document_id="CARE-01", status="active", policy_authority="official")
    )
    chunk_b = DocumentChunk(
        chunk_id="card-tumbler",
        filename="12-breeze-tumbler-product-card.md",
        heading="Cleaning",
        content="The product card states that all components are dishwasher safe, with top rack recommended.",
        metadata=DocumentMetadata(document_id="PROD-01", status="active", policy_authority="official")
    )
    
    result = detector.detect_conflicts([chunk_a, chunk_b])
    assert result.has_conflict is True
    assert "Dishwasher" in result.topic
    assert len(result.conflicting_chunks) == 2
    assert "hand-wash" in result.interim_guidance.lower()


def test_conflict_detector_no_conflict_on_consistent_chunks():
    detector = ConflictDetector()
    
    chunk_1 = DocumentChunk(
        chunk_id="ship-us",
        filename="05-domestic-shipping.md",
        heading="Processing",
        content="Most orders require 1-2 business days for processing.",
        metadata=DocumentMetadata(document_id="SHIP-01", status="active", policy_authority="official")
    )
    chunk_2 = DocumentChunk(
        chunk_id="ship-intl",
        filename="06-international-shipping.md",
        heading="Canada",
        content="Canadian orders arrive within 5-9 business days.",
        metadata=DocumentMetadata(document_id="SHIP-02", status="active", policy_authority="official")
    )
    
    result = detector.detect_conflicts([chunk_1, chunk_2])
    assert result.has_conflict is False
