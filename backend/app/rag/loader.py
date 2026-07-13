"""
Knowledge Base loader — Milestone 1.

Walks the knowledge_base/ directory, parses each Markdown file's YAML
front-matter + body, validates it against DocumentMetadata/KnowledgeDocument
(schema.py), and returns a list ready for the future indexing/embedding step.
No embeddings, no vector store, no retrieval here — purely loading and
validating structured content, per the milestone's scope.
"""

import hashlib
import re
from pathlib import Path
from typing import List

import yaml

from app.rag.schema import DocumentMetadata, KnowledgeDocument

FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?\n)---\s*\n(.*)$", re.DOTALL)

# Repo layout: backend/knowledge_base/ sits alongside backend/app/
DEFAULT_KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"


class KnowledgeBaseLoadError(Exception):
    """Raised when a specific document fails to parse/validate — the loader
    collects these per-file rather than letting one bad file abort the
    entire load (see load_knowledge_base's `strict` parameter)."""


def _split_front_matter(raw_text: str, file_path: Path) -> tuple[dict, str]:
    match = FRONT_MATTER_PATTERN.match(raw_text)
    if not match:
        raise KnowledgeBaseLoadError(f"{file_path}: missing or malformed YAML front-matter block.")
    front_matter_raw, body = match.group(1), match.group(2)
    try:
        metadata_dict = yaml.safe_load(front_matter_raw) or {}
    except yaml.YAMLError as exc:
        raise KnowledgeBaseLoadError(f"{file_path}: invalid YAML front-matter — {exc}") from exc
    return metadata_dict, body.strip()


def _load_single_document(file_path: Path, base_dir: Path) -> KnowledgeDocument:
    raw_text = file_path.read_text(encoding="utf-8")
    metadata_dict, content = _split_front_matter(raw_text, file_path)

    try:
        metadata = DocumentMetadata(**metadata_dict)
    except Exception as exc:  # pydantic ValidationError, or a plain KeyError/TypeError from bad YAML shape
        raise KnowledgeBaseLoadError(f"{file_path}: invalid document metadata — {exc}") from exc

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return KnowledgeDocument(
        metadata=metadata,
        content=content,
        file_path=str(file_path.relative_to(base_dir)),
        content_hash=content_hash,
        char_count=len(content),
        word_count=len(content.split()),
    )


def load_knowledge_base(
    base_dir: Path = DEFAULT_KNOWLEDGE_BASE_DIR,
    strict: bool = True,
) -> List[KnowledgeDocument]:
    """Load every .md document under base_dir.

    strict=True (default): raise on the first malformed document — appropriate
        for CI/startup checks where a broken document should be caught immediately.
    strict=False: skip malformed documents and continue, returning whatever
        loaded successfully — appropriate for exploratory/interactive use.
    """
    if not base_dir.exists():
        raise KnowledgeBaseLoadError(f"Knowledge base directory not found: {base_dir}")

    documents: List[KnowledgeDocument] = []
    for file_path in sorted(base_dir.rglob("*.md")):
        if file_path.name.upper() == "README.MD":
            continue  # authoring documentation, not a knowledge base document
        try:
            documents.append(_load_single_document(file_path, base_dir))
        except KnowledgeBaseLoadError:
            if strict:
                raise
            continue  # best-effort mode: skip and keep going

    _validate_unique_ids(documents)
    return documents


def _validate_unique_ids(documents: List[KnowledgeDocument]) -> None:
    seen = {}
    for doc in documents:
        if doc.metadata.id in seen:
            raise KnowledgeBaseLoadError(
                f"Duplicate document id '{doc.metadata.id}' in {doc.file_path} and {seen[doc.metadata.id]}."
            )
        seen[doc.metadata.id] = doc.file_path


def load_document_by_id(document_id: str, base_dir: Path = DEFAULT_KNOWLEDGE_BASE_DIR) -> KnowledgeDocument:
    """Convenience lookup — loads the full base and returns one match.
    Fine for a knowledge base this size; a future module could index this
    by id directly if the corpus grows much larger."""
    for doc in load_knowledge_base(base_dir, strict=False):
        if doc.metadata.id == document_id:
            return doc
    raise KnowledgeBaseLoadError(f"No document found with id '{document_id}'.")
