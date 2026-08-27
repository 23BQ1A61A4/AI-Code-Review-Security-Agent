"""
Vector store + retrieval for the Secure Coding Knowledge Base.

Uses a TF-IDF vectorizer (scikit-learn) as the embedding model and cosine
similarity for nearest-neighbor search. This keeps the RAG pipeline fully
local (no external embedding API/network call required), which matters
for the demo running offline, while still following the standard
chunk -> embed -> index -> retrieve -> ground pattern.
"""
from __future__ import annotations

from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .indexer import Chunk, load_knowledge_base

# A few extra keyword aliases per source document, folded into the indexed
# text (not the displayed text) so a search for a document's own name/topic
# — e.g. "Code Smell" — reliably surfaces that document even when the exact
# word doesn't appear inside a chunk's body text.
DOC_KEYWORDS = {
    "owasp_top10": "owasp top 10 vulnerabilities security",
    "secure_coding_python": "python secure coding guidelines",
    "secure_coding_java": "java secure coding guidelines",
    "code_smells": "code smell code smells design issue anti-pattern",
}


class KnowledgeBaseRetriever:
    def __init__(self) -> None:
        self._chunks: List[Chunk] = load_knowledge_base()
        self._vectorizer = TfidfVectorizer(stop_words="english")
        corpus = [f"{DOC_KEYWORDS.get(c.source, '')} {c.text}" for c in self._chunks]
        self._matrix = self._vectorizer.fit_transform(corpus) if corpus else None

    def retrieve(self, query: str, top_k: int = 3) -> List[Chunk]:
        if not self._chunks or self._matrix is None:
            return []
        q_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self._matrix)[0]
        ranked = sorted(range(len(self._chunks)), key=lambda i: sims[i], reverse=True)
        results = [self._chunks[i] for i in ranked[:top_k] if sims[i] > 0]
        return results or [self._chunks[i] for i in ranked[:1]]

    def search(self, query: str, top_k: int = 8) -> List[tuple[Chunk, float]]:
        """Same retrieval as `retrieve`, but also returns the similarity
        score for each hit — used by the Knowledge Base search page so the
        user can see why a document matched."""
        if not self._chunks or self._matrix is None or not query.strip():
            return []
        q_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self._matrix)[0]
        ranked = sorted(range(len(self._chunks)), key=lambda i: sims[i], reverse=True)
        return [(self._chunks[i], float(sims[i])) for i in ranked[:top_k] if sims[i] > 0]

    def all_chunks(self) -> List[Chunk]:
        return list(self._chunks)


# Singleton — the index is small, build it once at process start.
_retriever: KnowledgeBaseRetriever | None = None


def get_retriever() -> KnowledgeBaseRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeBaseRetriever()
    return _retriever
