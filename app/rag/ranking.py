from typing import List, Tuple, Dict, Optional
from app.models.schemas import DocumentChunk


class MetadataRanker:
    """
    Applies generic metadata-aware precedence rules to candidate chunks.
    Enforces status (active vs superseded), authority (official vs none),
    and audience (customer vs internal) hierarchy without hardcoding filenames.
    """
    def __init__(self, all_chunks: Optional[List[DocumentChunk]] = None):
        self.doc_id_to_chunks: Dict[str, List[DocumentChunk]] = {}
        self.superseded_map: Dict[str, str] = {}  # old_doc_id -> new_doc_id
        if all_chunks:
            self._index_supersession(all_chunks)

    def _index_supersession(self, all_chunks: List[DocumentChunk]):
        """Builds supersession graph from chunk metadata."""
        for chunk in all_chunks:
            meta = chunk.metadata
            if meta.document_id:
                self.doc_id_to_chunks.setdefault(meta.document_id, []).append(chunk)
                if meta.superseded_by:
                    self.superseded_map[meta.document_id] = meta.superseded_by
                if meta.supersedes:
                    self.superseded_map[meta.supersedes] = meta.document_id

    def rank(
        self,
        candidates: List[Tuple[DocumentChunk, float]],
        top_k: int = 5,
        allow_internal: bool = False,
        allow_superseded: bool = False,
        relative_threshold: float = 0.22,
        min_score: float = 0.04
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Ranks and filters candidate chunks based on generic metadata precedence,
        absolute confidence floor, and relative score drop-off threshold.
        """
        ranked: List[Tuple[DocumentChunk, float]] = []

        for chunk, sim_score in candidates:
            meta = chunk.metadata
            score = sim_score

            # Rule 1: Non-authoritative / Draft / Unapproved exclusion
            # Documents marked policy_authority == "none" or customer_answering == False
            if meta.policy_authority == "none" or not meta.customer_answering or meta.status == "draft":
                if not allow_internal:
                    continue
                score *= 0.05

            # Rule 2: Superseded document handling
            if meta.status == "superseded":
                if not allow_superseded:
                    # Exclude superseded document from customer-facing authority
                    continue
                else:
                    score *= 0.2

            # Rule 3: Official Active Policy boost
            if meta.status == "active" and meta.policy_authority == "official":
                score *= 1.25

            # Rule 4: Audience alignment (customer vs internal)
            if meta.audience == "customer":
                score *= 1.1
            elif meta.audience == "internal" and not allow_internal:
                score *= 0.8

            ranked.append((chunk, score))

        # Sort descending by adjusted score
        ranked.sort(key=lambda x: x[1], reverse=True)

        if not ranked:
            return []

        # Dynamic confidence thresholding:
        # 1. Absolute floor (min_score)
        # 2. Relative drop-off: candidate from another document must score at least (max_score * relative_threshold)
        top_doc_file = ranked[0][0].filename
        max_score = ranked[0][1]
        score_cutoff = max(min_score, max_score * relative_threshold) if max_score > 0 else min_score

        # Deduplicate chunks & enforce dynamic confidence cutoff
        selected: List[Tuple[DocumentChunk, float]] = []
        seen_chunk_ids = set()
        for chunk, score in ranked:
            if score < min_score:
                continue
            # Chunks from other documents must satisfy relative_threshold cutoff
            if chunk.filename != top_doc_file and score < score_cutoff and len(selected) >= 1:
                continue
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                selected.append((chunk, score))
            if len(selected) >= top_k:
                break

        return selected
