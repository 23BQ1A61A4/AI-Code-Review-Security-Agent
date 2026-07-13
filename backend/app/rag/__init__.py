"""
RAG package.

Milestone 1 status — Secure Coding Knowledge Base (COMPLETE):
    schema.py         - DocumentMetadata, KnowledgeDocument, DocumentChunk
    loader.py          - parses knowledge_base/*.md into KnowledgeDocument objects
    indexing_prep.py   - chunks documents + builds a manifest (NO embeddings yet)

The knowledge base content itself (30 Markdown documents) lives in
backend/knowledge_base/, not under app/ — it's data, not application code,
so a future embedding step can read it directly without importing this
package's internals.

Still NOT implemented (a later module, after Milestone 1 is signed off):
    - Embedding generation (e.g. ChromaDB + Sentence-Transformers)
    - A vector store / index
    - retrieve(query) — actual similarity search
    - Wiring retrieval into the Conversational Code Assistant

indexing_prep.prepare_for_indexing() produces exactly the input a future
embedding step needs (List[DocumentChunk] + a manifest) and stops there,
on purpose, per the milestone's explicit scope.
"""
