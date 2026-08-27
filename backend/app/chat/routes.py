from flask import Blueprint, jsonify, request

from ..agents.llm_client import LLMUnavailable, generate
from ..rag.retriever import get_retriever

chat_bp = Blueprint("chat", __name__)

SEVERITY_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def _grounded_answer_local(question: str, chunks, analysis_context: dict | None) -> str:
    q = question.lower()
    parts: list[str] = []

    # If the question is about the user's most recent analysis, answer from it directly.
    if analysis_context:
        issues = analysis_context.get("security_issues") or []
        bugs = analysis_context.get("bugs") or []
        fixes = analysis_context.get("fixes") or []
        metrics = analysis_context.get("metrics") or {}
        code_smells = analysis_context.get("code_smells") or []
        filename = analysis_context.get("filename") or "your submitted code"

        # 1. Asking about fixes/remediations
        if any(k in q for k in ("how do i fix", "how to fix", "remediat", "suggested fix", "correct")):
            if fixes:
                parts.append(f"### Recommended Fixes for **{filename}**\n")
                for f in fixes:
                    parts.append(f"**{f['title']}**\n{f.get('recommendation', '')}\n```\n{f.get('corrected_code', '')}\n```\n")
            elif issues:
                top = max(issues, key=lambda i: SEVERITY_ORDER.get(i.get("severity", "Low"), 0))
                parts.append(f"For **{top['title']}**, ensure user input is never concatenated into queries/commands directly. Use parameterized APIs.")

        # 2. Asking about top security issues or vulnerabilities
        elif any(k in q for k in ("top security", "vulnerab", "worst", "biggest", "security issue", "danger")):
            if issues:
                top = max(issues, key=lambda i: SEVERITY_ORDER.get(i.get("severity", "Low"), 0))
                parts.append(
                    f"The top security issue in **{filename}** is "
                    f"**{top['title']}** ({top['severity']}, {top.get('owasp_category','-')}):\n{top.get('detail','')}"
                )
                match = next((f for f in fixes if top["title"].lower() in f.get("title", "").lower()), None)
                if match:
                    parts.append(f"\n**Suggested fix:** {match['recommendation']}\n```\n{match.get('corrected_code','')}\n```")
            else:
                parts.append(f"No OWASP security vulnerabilities were flagged in **{filename}**.")

        # 3. Asking about bugs / code smells
        elif any(k in q for k in ("bug", "code smell", "defect", "quality issue")):
            if bugs:
                parts.append(f"### Code Analysis Findings for **{filename}**:")
                for b in bugs:
                    parts.append(f"- **[{b.get('severity', 'Low')}] {b.get('title', '')}**: {b.get('detail', '')}")
            if code_smells and code_smells != ["No significant code smells detected."]:
                parts.append("\n**Code Smells:** " + ", ".join(code_smells))

        # 4. Asking about metrics / complexity / score
        elif any(k in q for k in ("complexity", "score", "metric", "maintainab", "quality score", "verdict")):
            parts.append(f"### Analysis Metrics for **{filename}**:")
            parts.append(f"- **PR Verdict:** {analysis_context.get('pr_verdict', 'N/A')}")
            parts.append(f"- **Security Score:** {metrics.get('security_score', 'N/A')}/100")
            parts.append(f"- **Quality Score:** {metrics.get('quality_score', 'N/A')}/100")
            parts.append(f"- **Maintainability:** {metrics.get('maintainability_score', 'N/A')}/100")
            parts.append(f"- **Complexity:** {metrics.get('complexity', 'N/A')}")

        # 5. Asking what the code does or for a general overview
        elif any(k in q for k in ("what does", "explain", "summary", "overview", "describe")):
            if analysis_context.get("summary"):
                parts.append(f"**Overview of {filename} ({analysis_context.get('language','')}):**\n{analysis_context['summary']}")

    # Ground the rest of the answer in the Secure Coding Knowledge Base
    if chunks:
        if parts:
            parts.append("\n---\n**Related Knowledge Base Guidelines:**")
        else:
            parts.append("### Secure Coding Knowledge Base:")
        for c in chunks:
            parts.append(f"\n#### {c.heading} ({c.source.replace('_',' ').title()})\n{c.text}")

    if not parts:
        parts.append(
            "I couldn't find a direct match in the knowledge base. Try asking about an OWASP category "
            "(e.g., SQL Injection, XSS, CSRF, Hardcoded Secrets), a secure coding practice, or questions about your latest analysis."
        )
    return "\n".join(parts)


@chat_bp.post("/api/chat")
def chat():
    body = request.get_json(force=True, silent=True) or {}
    message = (body.get("message") or "").strip()
    history = body.get("history") or []  # [{role, content}, ...]
    analysis_context = body.get("analysis_context")

    if not message:
        return jsonify({"detail": "`message` is required"}), 400

    retriever = get_retriever()
    chunks = retriever.retrieve(message, top_k=3)

    try:
        context_block = "\n\n".join(f"### {c.heading} ({c.source})\n{c.text}" for c in chunks)
        system = (
            "You are Sentinel's Conversational Code Assistant, an expert AI for secure software engineering.\n"
            "Answer the user's questions clearly, accurately, and concisely using markdown.\n"
            "Ground your answer in the secure coding knowledge base context and the user's recent code analysis below.\n"
            "Always provide concrete code snippets or remediations when discussing vulnerabilities.\n\n"
            f"KNOWLEDGE BASE CONTEXT:\n{context_block}\n\n"
            + (f"MOST RECENT ANALYSIS CONTEXT:\n{analysis_context}\n\n" if analysis_context else "")
        )
        convo = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
        prompt = f"{convo}\nuser: {message}" if convo else message
        reply = generate(prompt, system=system)
    except (LLMUnavailable, Exception):
        reply = _grounded_answer_local(message, chunks, analysis_context)

    return jsonify({
        "reply": reply,
        "sources": [{"source": c.source, "heading": c.heading} for c in chunks],
    })
