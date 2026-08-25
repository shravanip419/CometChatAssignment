import re
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.schemas import DocumentChunk


class ConflictResult(BaseModel):
    has_conflict: bool = False
    topic: str = ""
    conflicting_chunks: List[DocumentChunk] = Field(default_factory=list)
    explanation: str = ""
    interim_guidance: str = ""


class ConflictDetector:
    """
    Generic conflict detector that identifies genuine contradictions
    between active, official documents without hardcoded filenames.

    Each entry in OPPOSING_PATTERNS is a 5-tuple:
        (pattern_a, pattern_b, topic_desc, topic_keywords, safe_guidance)

    topic_keywords: list of lowercase words used to decide whether the current
    query is relevant to this conflict during corpus-expansion searches.
    """

    OPPOSING_PATTERNS = [
        (
            re.compile(r"\b(hand-wash|hand wash|hand-washed)\b", re.IGNORECASE),
            re.compile(r"\b(dishwasher safe|dishwasher-safe)\b", re.IGNORECASE),
            "Dishwasher Safety & Cleaning Method",
            ["dishwasher", "wash", "clean", "tumbler", "breeze"],
            "Hand-wash the stainless-steel body and place only top-rack compatible parts (such as the lid) in the dishwasher.",
        ),
    ]

    def detect_conflicts(
        self,
        retrieved_chunks: List[DocumentChunk],
        all_corpus_chunks: Optional[List[DocumentChunk]] = None,
        query: Optional[str] = None,
    ) -> ConflictResult:
        """
        Scans retrieved active official chunks for contradictory authoritative statements.
        For each OPPOSING_PATTERN pair, checks whether both sides appear across distinct
        source files in the retrieved set (with optional corpus expansion).
        """
        # Work only with active, official sources
        active_official = [
            c for c in retrieved_chunks
            if c.metadata.status == "active" and c.metadata.policy_authority == "official"
        ]

        if not active_official:
            return ConflictResult(has_conflict=False)

        q_lower = (query or "").lower()

        for pattern_a, pattern_b, topic_desc, topic_keywords, safe_guidance in self.OPPOSING_PATTERNS:
            matching_a: List[DocumentChunk] = []
            matching_b: List[DocumentChunk] = []

            for chunk in active_official:
                text = f"{chunk.heading}\n{chunk.content}"
                if pattern_a.search(text):
                    matching_a.append(chunk)
                if pattern_b.search(text):
                    matching_b.append(chunk)

            # One side missing from retrieved set → try corpus expansion when the
            # query is relevant to this conflict topic
            if (matching_a and not matching_b) or (matching_b and not matching_a):
                is_topic_relevant = any(kw in q_lower for kw in topic_keywords)
                if is_topic_relevant and all_corpus_chunks:
                    target_pattern = pattern_b if matching_a else pattern_a
                    for corpus_chunk in all_corpus_chunks:
                        if (
                            corpus_chunk.metadata.status == "active"
                            and corpus_chunk.metadata.policy_authority == "official"
                        ):
                            chunk_text = f"{corpus_chunk.heading} {corpus_chunk.content}"
                            if target_pattern.search(chunk_text):
                                if matching_a:
                                    matching_b.append(corpus_chunk)
                                else:
                                    matching_a.append(corpus_chunk)
                                break

            # Both sides present across distinct files → genuine conflict
            files_a = {c.filename for c in matching_a}
            files_b = {c.filename for c in matching_b}

            if matching_a and matching_b and (files_a != files_b or len(files_a) > 1 or len(files_b) > 1):
                conflicting = list({c.chunk_id: c for c in (matching_a + matching_b)}.values())
                explanation = (
                    f"Current official documents contain contradictory guidance regarding "
                    f"{topic_desc}. One official document specifies one approach while "
                    f"another states the opposite."
                )
                return ConflictResult(
                    has_conflict=True,
                    topic=topic_desc,
                    conflicting_chunks=conflicting,
                    explanation=explanation,
                    interim_guidance=safe_guidance,
                )

        return ConflictResult(has_conflict=False)
