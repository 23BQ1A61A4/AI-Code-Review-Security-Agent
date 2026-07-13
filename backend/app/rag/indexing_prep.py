"""
Indexing preparation — Milestone 1.

Splits each KnowledgeDocument into smaller DocumentChunk objects sized for
retrieval (a full document is usually too large/unfocused for a single
embedding to represent well) and builds a manifest summarizing the prepared
corpus.

Deliberately stops here: no embedding model is called, no vector store is
touched. This module's output (chunks + manifest) is exactly what a future
RAG module would feed into an embedding step — see rag_consumption notes in
the module README for the intended handoff shape.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from app.rag.schema import DocumentChunk, KnowledgeDocument

DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP_CHARS = 150


def chunk_document(
    document: KnowledgeDocument,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> List[DocumentChunk]:
    """Paragraph-aware chunking: accumulate whole paragraphs (split on blank
    lines / Markdown headings) up to max_chars, carrying a small tail of the
    previous chunk forward as overlap so a chunk boundary doesn't sever
    context a retriever would need. A paragraph longer than max_chars on its
    own is kept whole rather than being cut mid-sentence — retrieval quality
    from a slightly-oversized chunk is better than a fragment that stops
    mid-thought.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", document.content) if p.strip()]
    if not paragraphs:
        return []

    chunks: List[DocumentChunk] = []
    current = ""

    def flush(text: str):
        if not text.strip():
            return
        index = len(chunks)
        chunks.append(DocumentChunk(
            chunk_id=f"{document.metadata.id}::chunk-{index}",
            document_id=document.metadata.id,
            chunk_index=index,
            text=text.strip(),
            category=document.metadata.category,
            owasp_category=document.metadata.owasp_category,
            cwe_id=document.metadata.cwe_id,
            languages=document.metadata.languages,
            tags=document.metadata.tags,
            source_title=document.metadata.title,
            source_file_path=document.file_path,
        ))

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        # Current chunk is full — flush it, then start the next one, seeded
        # with a small overlap tail from what was just flushed for context
        # continuity across the boundary.
        flush(current)
        tail = current[-overlap_chars:] if len(current) > overlap_chars else current
        current = f"{tail}\n\n{paragraph}" if tail else paragraph

    flush(current)
    return chunks


def chunk_all_documents(
    documents: List[KnowledgeDocument],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> List[DocumentChunk]:
    all_chunks: List[DocumentChunk] = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc, max_chars, overlap_chars))
    return all_chunks


def build_manifest(documents: List[KnowledgeDocument], chunks: List[DocumentChunk]) -> Dict:
    """A JSON-serializable summary of the prepared corpus — useful as a
    sanity check before a future embedding step runs, and as a record of
    what was indexed and when."""
    category_counts: Dict[str, int] = {}
    for doc in documents:
        category_counts[doc.metadata.category.value] = category_counts.get(doc.metadata.category.value, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "documents_by_category": category_counts,
        "average_chunks_per_document": round(len(chunks) / len(documents), 2) if documents else 0,
        "documents": [
            {
                "id": doc.metadata.id,
                "title": doc.metadata.title,
                "category": doc.metadata.category.value,
                "file_path": doc.file_path,
                "content_hash": doc.content_hash,
                "word_count": doc.word_count,
            }
            for doc in documents
        ],
    }


def write_manifest(manifest: Dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def prepare_for_indexing(
    documents: List[KnowledgeDocument],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> tuple[List[DocumentChunk], Dict]:
    """The single entry point a future indexing step would call: load
    documents (via loader.py), pass them here, get back chunks ready to
    embed plus a manifest describing what was prepared."""
    chunks = chunk_all_documents(documents, max_chars, overlap_chars)
    manifest = build_manifest(documents, chunks)
    return chunks, manifest
