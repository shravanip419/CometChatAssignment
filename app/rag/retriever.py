from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from app.models.schemas import DocumentChunk, SourceCitation
from app.rag.chunker import build_kb_chunks
from app.rag.embeddings import EmbeddingEngine
from app.rag.index import VectorIndex
from app.rag.ranking import MetadataRanker
from app.rag.conflict_detector import ConflictDetector, ConflictResult
from app.config import KNOWLEDGE_BASE_DIR


class KnowledgeRetriever:
    """
    RAG Retriever coordinating vector index search, metadata precedence ranking,
    and generic source conflict detection.
    """
    def __init__(
        self,
        kb_dir: Optional[Path] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        ranker: Optional[MetadataRanker] = None,
        conflict_detector: Optional[ConflictDetector] = None,
    ):
        self.kb_dir = kb_dir or KNOWLEDGE_BASE_DIR
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.chunks: List[DocumentChunk] = build_kb_chunks(self.kb_dir)
        self.index = VectorIndex(self.chunks, self.embedding_engine)
        self.ranker = ranker or MetadataRanker(self.chunks)
        self.conflict_detector = conflict_detector or ConflictDetector()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        allow_internal: bool = False,
        allow_superseded: bool = False,
        relative_threshold: float = 0.22,
        min_score: float = 0.04
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Retrieves relevant chunks using vector search, applies metadata-aware
        precedence ranking, dynamic confidence thresholding, and ensures conflicting authoritative sources are surfaced.
        """
        if not self.chunks:
            return []

        # Step 1: Candidate vector retrieval from index
        candidates = self.index.search(query, top_n=max(top_k * 3, 10))
        if not candidates:
            return []

        # Step 2: Metadata precedence ranking (active > superseded, official > draft/none)
        ranked = self.ranker.rank(
            candidates,
            top_k=top_k,
            allow_internal=allow_internal,
            allow_superseded=allow_superseded,
            relative_threshold=relative_threshold,
            min_score=min_score
        )

        # Step 3: Generic conflict check
        retrieved_chunks_only = [c for c, _ in ranked]
        conflict_res = self.conflict_detector.detect_conflicts(retrieved_chunks_only, self.chunks, query=query)

        # If a genuine conflict is detected, ensure all conflicting chunks are included
        if conflict_res.has_conflict:
            seen_ids = {c.chunk_id for c, _ in ranked}
            for conf_chunk in conflict_res.conflicting_chunks:
                if conf_chunk.chunk_id not in seen_ids:
                    ranked.append((conf_chunk, 0.95))
                    seen_ids.add(conf_chunk.chunk_id)

        return ranked

    def check_conflicts(self, chunks: List[DocumentChunk], query: Optional[str] = None) -> ConflictResult:
        """Exposes conflict detection helper for response generation."""
        return self.conflict_detector.detect_conflicts(chunks, self.chunks, query=query)
