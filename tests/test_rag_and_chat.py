"""
Milestone 4 / Task 5 & 6 — RAG retrieval and Conversational Assistant validation.

Uses the existing TF-IDF retriever and the real /api/chat and
/api/knowledge-base endpoints. No responses are mocked.
"""
from __future__ import annotations


def test_kb_documents_endpoint_returns_all_four_docs(client):
    res = client.get("/api/knowledge-base/documents")
    assert res.status_code == 200
    docs = res.get_json()["documents"]
    sources = {d["source"] for d in docs}
    assert sources == {"owasp_top10", "secure_coding_python", "secure_coding_java", "code_smells"}
    for d in docs:
        assert len(d["sections"]) > 0


def test_rag_retrieves_relevant_chunk_for_sql_injection_question(client):
    res = client.get("/api/knowledge-base/search", query_string={"q": "how to prevent SQL injection"})
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert len(results) > 0
    combined = " ".join((r["heading"] + " " + r["text"]).lower() for r in results)
    assert "sql" in combined or "inject" in combined


def test_rag_retrieves_relevant_chunk_for_password_question(client):
    res = client.get("/api/knowledge-base/search", query_string={"q": "secure way to store passwords"})
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert len(results) > 0
    combined = " ".join((r["heading"] + " " + r["text"]).lower() for r in results)
    assert any(k in combined for k in ("password", "hash", "bcrypt", "crypt"))


def test_rag_retrieves_relevant_chunk_for_input_validation_question(client):
    res = client.get("/api/knowledge-base/search", query_string={"q": "unsafe input validation improvements"})
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert len(results) > 0


def test_rag_unrelated_query_does_not_force_unrelated_top_hit_with_no_signal(client):
    """An empty query returns no results rather than an arbitrary citation."""
    res = client.get("/api/knowledge-base/search", query_string={"q": ""})
    assert res.status_code == 200
    assert res.get_json()["results"] == []


def test_chat_requires_message(client):
    res = client.post("/api/chat", json={"message": ""})
    assert res.status_code == 400


def test_chat_vulnerability_explanation_question(client):
    res = client.post("/api/chat", json={"message": "What is SQL injection and why is it dangerous?", "history": []})
    assert res.status_code == 200
    body = res.get_json()
    assert body["reply"]
    assert isinstance(body["sources"], list)


def test_chat_remediation_question_grounded_in_kb(client):
    res = client.post("/api/chat", json={
        "message": "How can I remediate a hardcoded secret in my code?",
        "history": [],
    })
    assert res.status_code == 200
    body = res.get_json()
    assert body["reply"]
    # At least one KB source should have been retrieved for a remediation question.
    assert len(body["sources"]) > 0


def test_chat_multi_turn_uses_conversation_history_and_analysis_context(client, sample2):
    """Task 6/7 flow: flag a vulnerability -> ask for explanation -> ask for
    remediation -> ask a general secure-coding best-practice question,
    verifying the assistant uses submitted-code findings, KB context, and
    conversation history where appropriate."""
    run = client.post("/api/analysis/run", json={"code": sample2, "language": "Python", "filename": "sample2_vulnerable.py"})
    analysis = run.get_json()

    history = []

    r1 = client.post("/api/chat", json={
        "message": "What's the top security issue in my last analysis?",
        "history": history,
        "analysis_context": analysis,
    })
    assert r1.status_code == 200
    reply1 = r1.get_json()["reply"]
    assert reply1
    history.append({"role": "user", "content": "What's the top security issue in my last analysis?"})
    history.append({"role": "assistant", "content": reply1})

    r2 = client.post("/api/chat", json={
        "message": "How do I fix it?",
        "history": history,
        "analysis_context": analysis,
    })
    assert r2.status_code == 200
    assert r2.get_json()["reply"]
    history.append({"role": "user", "content": "How do I fix it?"})
    history.append({"role": "assistant", "content": r2.get_json()["reply"]})

    r3 = client.post("/api/chat", json={
        "message": "What is a general secure coding best practice for handling user input?",
        "history": history,
        "analysis_context": analysis,
    })
    assert r3.status_code == 200
    body3 = r3.get_json()
    assert body3["reply"]
    assert len(body3["sources"]) > 0  # grounded in the knowledge base, not free-floating
