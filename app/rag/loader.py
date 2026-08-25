import re
from pathlib import Path
from typing import Dict, Any, Tuple
import yaml
from app.models.schemas import DocumentMetadata


def parse_frontmatter(content: str) -> Tuple[DocumentMetadata, str]:
    """
    Parses YAML frontmatter from markdown content.
    Returns (DocumentMetadata, body_text).
    """
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = frontmatter_pattern.match(content)
    
    if not match:
        return DocumentMetadata(), content
    
    yaml_text = match.group(1)
    body_text = content[match.end():]
    
    try:
        raw_meta = yaml.safe_load(yaml_text) or {}
    except Exception:
        raw_meta = {}
        
    metadata = DocumentMetadata(
        document_id=str(raw_meta.get("document_id", "")),
        title=str(raw_meta.get("title", "")),
        status=str(raw_meta.get("status", "active")).lower(),
        effective_date=str(raw_meta.get("effective_date")) if raw_meta.get("effective_date") else None,
        superseded_date=str(raw_meta.get("superseded_date")) if raw_meta.get("superseded_date") else None,
        last_reviewed=str(raw_meta.get("last_reviewed")) if raw_meta.get("last_reviewed") else None,
        audience=str(raw_meta.get("audience", "customer")).lower(),
        policy_authority=str(raw_meta.get("policy_authority", "official")).lower(),
        supersedes=str(raw_meta.get("supersedes")) if raw_meta.get("supersedes") else None,
        superseded_by=str(raw_meta.get("superseded_by")) if raw_meta.get("superseded_by") else None,
        customer_answering=raw_meta.get("customer_answering", True),
    )
    
    return metadata, body_text.strip()


def load_knowledge_base(kb_dir: Path) -> Dict[str, Tuple[DocumentMetadata, str]]:
    """
    Loads all markdown files in kb_dir.
    Returns a dict mapping filename -> (DocumentMetadata, body_text).
    """
    documents = {}
    for md_file in sorted(kb_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(text)
        documents[md_file.name] = (metadata, body)
    return documents
