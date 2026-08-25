import numpy as np
from typing import List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from app.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
import re

def _stem_token(word: str) -> str:
    """Lightweight rule-based suffix stemmer for retrieval normalization."""
    word = word.lower()
    for suffix in ["ly", "ing", "ies", "es", "s", "ed", "ment", "able", "al", "tion", "ation"]:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            word = word[:-len(suffix)]
    return word

def _custom_tokenizer(text: str) -> List[str]:
    tokens = re.findall(r"(?u)\b[\w-]+\b", text.lower())
    return [_stem_token(t) for t in tokens if len(t) > 1 and t not in ENGLISH_STOP_WORDS]


class EmbeddingEngine:
    """
    Handles generating embeddings for text chunks and queries.
    Uses OpenAI embeddings if OPENAI_API_KEY is available,
    otherwise falls back to a deterministic, high-quality TF-IDF / subword vectorizer.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = OPENAI_EMBEDDING_MODEL):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model
        self.use_openai = bool(self.api_key and self.api_key.startswith("sk-"))
        self._openai_client = None
        self._tfidf_vectorizer: Optional[TfidfVectorizer] = None
        
        if self.use_openai:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.api_key)
            except Exception:
                self.use_openai = False

    def fit_fallback(self, corpus_texts: List[str]):
        """Fits the fallback vectorizer on the full corpus."""
        self._tfidf_vectorizer = TfidfVectorizer(
            tokenizer=_custom_tokenizer,
            ngram_range=(1, 2),
            sublinear_tf=True,
            token_pattern=None
        )
        self._tfidf_vectorizer.fit(corpus_texts)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embeds a list of texts into a 2D numpy array of shape (len(texts), dim)."""
        if not texts:
            return np.empty((0, 0))
            
        if self.use_openai and self._openai_client:
            try:
                # Batch request to OpenAI
                response = self._openai_client.embeddings.create(
                    input=texts,
                    model=self.model
                )
                embeddings = [item.embedding for item in response.data]
                arr = np.array(embeddings, dtype=np.float32)
                # Normalize
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1e-10
                return arr / norms
            except Exception:
                # Fall back to local
                pass
                
        if self._tfidf_vectorizer is None:
            self.fit_fallback(texts)
            
        matrix = self._tfidf_vectorizer.transform(texts).toarray()
        arr = np.array(matrix, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        return arr / norms

    def embed_query(self, query: str) -> np.ndarray:
        """Embeds a single query into a 1D numpy array."""
        embeddings = self.embed_texts([query])
        if len(embeddings) > 0:
            return embeddings[0]
        return np.empty((0,))
