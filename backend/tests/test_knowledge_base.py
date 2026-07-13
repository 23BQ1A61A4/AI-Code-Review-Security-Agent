"""
Unit tests for app/rag/loader.py and app/rag/indexing_prep.py.

Run with:
    pytest tests/test_knowledge_base.py -v

No LLM, no network, no embeddings — pure loading/parsing/chunking logic.
"""

import pytest

from app.rag.indexing_prep import build_manifest, chunk_all_documents, chunk_document, prepare_for_indexing
from app.rag.loader import KnowledgeBaseLoadError, load_knowledge_base
from app.rag.schema import KnowledgeCategory


@pytest.fixture(scope="module")
def documents():
    return load_knowledge_base()


class TestLoader:
    def test_loads_expected_document_count(self, documents):
        assert len(documents) == 30

    def test_every_document_has_required_metadata(self, documents):
        for doc in documents:
            assert doc.metadata.id
            assert doc.metadata.title
            assert doc.metadata.category in KnowledgeCategory
            assert doc.content.strip()

    def test_document_ids_are_unique(self, documents):
        ids = [doc.metadata.id for doc in documents]
        assert len(ids) == len(set(ids))

    def test_content_hash_is_deterministic(self, documents):
        doc = documents[0]
        import hashlib
        expected = hashlib.sha256(doc.content.encode("utf-8")).hexdigest()
        assert doc.content_hash == expected

    def test_word_and_char_counts_are_positive(self, documents):
        for doc in documents:
            assert doc.word_count > 0
            assert doc.char_count > 0

    def test_all_seven_categories_are_represented(self, documents):
        categories_found = {doc.metadata.category for doc in documents}
        assert categories_found == set(KnowledgeCategory)

    def test_owasp_top_10_has_exactly_ten_documents(self, documents):
        owasp_docs = [d for d in documents if d.metadata.category == KnowledgeCategory.OWASP_TOP_10]
        assert len(owasp_docs) == 10

    def test_known_topic_ids_present(self, documents):
        ids = {doc.metadata.id for doc in documents}
        expected_subset = {
            "sql-injection", "cross-site-scripting-xss", "cross-site-request-forgery-csrf",
            "command-injection", "path-traversal", "server-side-request-forgery-ssrf",
            "hardcoded-secrets", "broken-access-control", "authentication", "authorization",
            "input-validation", "output-encoding", "cryptography", "logging", "error-handling",
            "secure-file-upload", "secure-password-storage", "secure-session-management",
            "secure-python-coding", "secure-java-coding",
        }
        assert expected_subset.issubset(ids)

    def test_file_path_is_relative_and_traceable(self, documents):
        for doc in documents:
            assert not doc.file_path.startswith("/")
            assert doc.file_path.endswith(".md")

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(KnowledgeBaseLoadError):
            load_knowledge_base(base_dir=tmp_path / "does_not_exist")

    def test_malformed_front_matter_raises_in_strict_mode(self, tmp_path):
        bad_dir = tmp_path / "kb"
        bad_dir.mkdir()
        (bad_dir / "broken.md").write_text("no front matter here at all")
        with pytest.raises(KnowledgeBaseLoadError):
            load_knowledge_base(base_dir=bad_dir, strict=True)

    def test_malformed_front_matter_skipped_in_non_strict_mode(self, tmp_path):
        bad_dir = tmp_path / "kb"
        bad_dir.mkdir()
        (bad_dir / "broken.md").write_text("no front matter here at all")
        (bad_dir / "good.md").write_text(
            "---\nid: good-doc\ntitle: Good Doc\ncategory: operations\n---\n\nSome content.\n"
        )
        docs = load_knowledge_base(base_dir=bad_dir, strict=False)
        assert len(docs) == 1
        assert docs[0].metadata.id == "good-doc"

    def test_duplicate_ids_raise(self, tmp_path):
        bad_dir = tmp_path / "kb"
        bad_dir.mkdir()
        content = "---\nid: dup-id\ntitle: One\ncategory: operations\n---\n\nContent A.\n"
        (bad_dir / "a.md").write_text(content)
        (bad_dir / "b.md").write_text(content.replace("Content A.", "Content B."))
        with pytest.raises(KnowledgeBaseLoadError):
            load_knowledge_base(base_dir=bad_dir, strict=True)


class TestIndexingPrep:
    def test_chunk_document_produces_nonempty_chunks(self, documents):
        doc = documents[0]
        chunks = chunk_document(doc)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.text.strip()
            assert chunk.document_id == doc.metadata.id

    def test_chunk_ids_are_unique_and_sequential(self, documents):
        doc = documents[0]
        chunks = chunk_document(doc)
        expected_ids = [f"{doc.metadata.id}::chunk-{i}" for i in range(len(chunks))]
        assert [c.chunk_id for c in chunks] == expected_ids

    def test_chunks_carry_denormalized_metadata(self, documents):
        doc = next(d for d in documents if d.metadata.id == "sql-injection")
        chunks = chunk_document(doc)
        assert all(c.category == doc.metadata.category for c in chunks)
        assert all(c.cwe_id == doc.metadata.cwe_id for c in chunks)
        assert all(c.source_title == doc.metadata.title for c in chunks)

    def test_small_max_chars_produces_more_chunks_than_large(self, documents):
        doc = next(d for d in documents if d.word_count > 100)
        small_chunks = chunk_document(doc, max_chars=200)
        large_chunks = chunk_document(doc, max_chars=5000)
        assert len(small_chunks) >= len(large_chunks)

    def test_chunk_all_documents_covers_every_document(self, documents):
        chunks = chunk_all_documents(documents)
        chunked_doc_ids = {c.document_id for c in chunks}
        all_doc_ids = {d.metadata.id for d in documents}
        assert chunked_doc_ids == all_doc_ids

    def test_manifest_counts_match(self, documents):
        chunks = chunk_all_documents(documents)
        manifest = build_manifest(documents, chunks)
        assert manifest["document_count"] == len(documents)
        assert manifest["chunk_count"] == len(chunks)
        assert sum(manifest["documents_by_category"].values()) == len(documents)
        assert len(manifest["documents"]) == len(documents)

    def test_prepare_for_indexing_end_to_end(self, documents):
        chunks, manifest = prepare_for_indexing(documents)
        assert len(chunks) > 0
        assert manifest["document_count"] == 30
        assert manifest["chunk_count"] == len(chunks)

    def test_no_paragraph_content_lost_in_chunking(self, documents):
        # Every non-trivial word from the source document should appear
        # somewhere across its chunks (loose check — chunking must not
        # silently drop content).
        doc = next(d for d in documents if d.metadata.id == "authentication")
        chunks = chunk_document(doc)
        combined = " ".join(c.text for c in chunks)
        for keyword in ["bcrypt", "Argon2", "session"]:
            assert keyword in combined
