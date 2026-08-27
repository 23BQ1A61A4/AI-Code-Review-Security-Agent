"""
Secure Coding Knowledge Base indexer.

Loads every markdown file under rag/knowledge_base/, splits it into
`##`-level chunks (each chunk = one topic, e.g. "A03: Injection"), and
exposes them as a flat list of {id, source, heading, text} dicts that the
retriever can vectorize. This is the "chunking" step of the RAG pipeline
described in Milestone 1 of the project spec.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

KB_DIR = Path(__file__).parent / "knowledge_base"


@dataclass
class Chunk:
    id: str
    source: str
    heading: str
    text: str


def _split_markdown(source_name: str, raw: str) -> List[Chunk]:
    """Split a markdown doc into chunks on '## ' headings."""
    parts = re.split(r"(?m)^## ", raw)
    chunks: List[Chunk] = []
    # parts[0] is the '# Title' preamble before the first '## '
    for i, part in enumerate(parts[1:], start=1):
        lines = part.strip().split("\n", 1)
        heading = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        text = f"{heading}\n{body}"
        chunks.append(
            Chunk(id=f"{source_name}:{i}", source=source_name, heading=heading, text=text)
        )
    return chunks


def load_knowledge_base() -> List[Chunk]:
    chunks: List[Chunk] = []
    for path in sorted(KB_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        chunks.extend(_split_markdown(path.stem, raw))
    return chunks
