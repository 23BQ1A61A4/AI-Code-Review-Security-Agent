"""
Knowledge Base document schema — Milestone 1.

Defines the shape every knowledge base document conforms to once loaded,
independent of how it's stored on disk (currently Markdown + YAML
front-matter) or how it will later be embedded/indexed. The loader
(loader.py) is responsible for producing these objects; the future RAG
retriever (a later module) will consume them — neither needs to change if
the other's implementation changes, as long as this schema holds.
"""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class KnowledgeCategory(str, Enum):
    """Top-level grouping — mirrors the knowledge_base/ folder structure."""
    OWASP_TOP_10 = "owasp_top_10"
    SECURE_CODING = "secure_coding"
    VULNERABILITY = "vulnerability"
    IDENTITY = "identity"
    DATA_HANDLING = "data_handling"
    OPERATIONS = "operations"
    FILE_AND_SESSION = "file_and_session"


class DocumentMetadata(BaseModel):
    """Parsed from each document's YAML front-matter block."""
    id: str = Field(..., min_length=1)  # stable, unique, kebab-case identifier
    title: str = Field(..., min_length=1)
    category: KnowledgeCategory
    owasp_category: Optional[str] = None
    cwe_id: Optional[str] = None
    languages: List[str] = Field(default_factory=list)  # e.g. ["python", "java"]
    tags: List[str] = Field(default_factory=list)
    source: str = "internal-authored"
    version: int = 1
    last_updated: Optional[date] = None


class KnowledgeDocument(BaseModel):
    """A single fully-loaded knowledge base document: metadata + body content,
    plus provenance fields the loader fills in (never hand-authored)."""
    metadata: DocumentMetadata
    content: str  # the Markdown body, front-matter stripped
    file_path: str  # relative path under knowledge_base/, for traceability
    content_hash: str  # sha256 of `content` — lets a future indexer detect changes
    char_count: int
    word_count: int


class DocumentChunk(BaseModel):
    """A retrieval-sized slice of a KnowledgeDocument, produced by the
    (embedding-free) chunker in indexing_prep.py. This is what a future RAG
    pipeline will actually embed and index — not the full document, which is
    usually too large for a single embedding to represent well."""
    chunk_id: str  # f"{document_id}::chunk-{index}"
    document_id: str
    chunk_index: int
    text: str
    # A flattened, retrieval-friendly subset of the parent document's
    # metadata, denormalized onto the chunk so a future vector store can
    # filter/facet without a join back to the source document.
    category: KnowledgeCategory
    owasp_category: Optional[str] = None
    cwe_id: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    source_title: str
    source_file_path: str
