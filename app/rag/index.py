import numpy as np
from typing import List, Tuple, Optional
from app.models.schemas import DocumentChunk
from app.rag.embeddings import EmbeddingEngine


class VectorIndex:
    """
    Pure vector index for storing document chunks and performing candidate vector search.
    Does not contain business rules, hardcoded filename boosts, or precedence filtering.
    """
    def __init__(self, chunks: List[DocumentChunk], embedding_engine: Optional[EmbeddingEngine] = None):
        self.chunks = chunks
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.vectors: np.ndarray = np.empty((0, 0))
        self._build_index()

    def _build_index(self):
        """Generates embeddings for all chunks."""
        if not self.chunks:
            self.vectors = np.empty((0, 0))
            return

        chunk_texts = [
            f"{c.metadata.title or ''} — {c.heading}\n{c.content}"
            for c in self.chunks
        ]
        self.embedding_engine.fit_fallback(chunk_texts)
        self.vectors = self.embedding_engine.embed_texts(chunk_texts)

    def search(self, query: str, top_n: int = 10) -> List[Tuple[DocumentChunk, float]]:
        """
        Computes cosine similarity between query and all chunks in index.
        Returns top_n (DocumentChunk, similarity_score) pairs sorted by score descending.
        """
        if not self.chunks or len(self.vectors) == 0:
            return []

        query_vec = self.embedding_engine.embed_query(query)
        if query_vec.shape[0] == 0:
            return []

        # Cosine similarity (vectors are normalized)
        scores = np.dot(self.vectors, query_vec)
        
        candidates = [
            (self.chunks[i], float(scores[i]))
            for i in range(len(self.chunks))
        ]
        
        # Sort descending by similarity score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
