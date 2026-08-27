"""
Knowledge Base browse + search routes.

Two endpoints for the frontend's new Knowledge Base page:
  GET /api/knowledge-base/documents  — the four secure-coding documents in
                                        full, grouped by source file, for
                                        the "browse" view.
  GET /api/knowledge-base/search?q=  — keyword search over the same content
                                        using the existing RAG retriever
                                        (TF-IDF + cosine similarity), for
                                        the search box.
Both reuse the RAG indexer/retriever already built for the Conversational
Code Assistant — this page is just a visible window into the same index.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from .indexer import load_knowledge_base
from .retriever import get_retriever

kb_bp = Blueprint("knowledge_base", __name__)

DOC_TITLES = {
    "owasp_top10": "OWASP Top 10",
    "secure_coding_python": "Secure Coding (Python)",
    "secure_coding_java": "Secure Coding (Java)",
    "code_smells": "Code Smells",
}


@kb_bp.get("/api/knowledge-base/documents")
def list_documents():
    chunks = load_knowledge_base()
    docs: dict[str, dict] = {}
    for c in chunks:
        doc = docs.setdefault(c.source, {
            "source": c.source,
            "title": DOC_TITLES.get(c.source, c.source.replace("_", " ").title()),
            "sections": [],
        })
        doc["sections"].append({"heading": c.heading, "text": c.text.split("\n", 1)[-1].strip()})
    # stable, human-friendly order
    order = ["owasp_top10", "secure_coding_python", "secure_coding_java", "code_smells"]
    ordered = [docs[s] for s in order if s in docs] + [v for k, v in docs.items() if k not in order]
    return jsonify({"documents": ordered})


@kb_bp.get("/api/knowledge-base/search")
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"query": q, "results": []})
    retriever = get_retriever()
    hits = retriever.search(q, top_k=8)
    results = [{
        "source": c.source,
        "title": DOC_TITLES.get(c.source, c.source.replace("_", " ").title()),
        "heading": c.heading,
        "text": c.text.split("\n", 1)[-1].strip(),
        "score": round(score, 4),
    } for c, score in hits]
    return jsonify({"query": q, "results": results})
