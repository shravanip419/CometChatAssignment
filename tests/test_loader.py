import pytest
from app.rag.loader import load_knowledge_base, parse_frontmatter
from app.config import KNOWLEDGE_BASE_DIR


def test_load_all_knowledge_base_files():
    docs = load_knowledge_base(KNOWLEDGE_BASE_DIR)
    assert len(docs) == 14
    for filename, (meta, body) in docs.items():
        assert filename.endswith(".md")
        assert meta.document_id != ""
        assert meta.status in ("active", "superseded", "draft")
        assert meta.policy_authority in ("official", "none")
        assert len(body) > 0


def test_parse_frontmatter_supersession():
    sample = """---
document_id: TEST-02
title: Active Returns
status: active
effective_date: 2026-04-01
audience: customer
policy_authority: official
supersedes: TEST-01
---

# Active Returns

## Section 1
Body text.
"""
    meta, body = parse_frontmatter(sample)
    assert meta.document_id == "TEST-02"
    assert meta.status == "active"
    assert meta.supersedes == "TEST-01"
    assert meta.policy_authority == "official"
    assert "## Section 1" in body
