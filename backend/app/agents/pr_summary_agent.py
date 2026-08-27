"""
PR Summary Agent (Milestone 3).

Compiles the Code Analysis, Security, and Remediation agents' output into a
structured, human-readable review: severity-weighted scores, a complexity
rating, a PR verdict, an executive-summary paragraph, and dynamically-derived
best-practice and performance suggestions tailored to the analyzed code.
"""
from __future__ import annotations

import json

from .llm_client import LLMUnavailable, extract_json, generate

SEVERITY_WEIGHT = {"Critical": 30, "High": 15, "Medium": 8, "Low": 3}


def _score(issues: list[dict]) -> int:
    penalty = sum(SEVERITY_WEIGHT.get(i.get("severity", "Low"), 3) for i in issues)
    return max(0, 100 - penalty)


def _dynamic_best_practices(language: str, bugs: list[dict], security_issues: list[dict], code_smells: list[str]) -> list[str]:
    practices = []
    sec_titles = " ".join(i.get("title", "").lower() + " " + i.get("detail", "").lower() for i in security_issues)
    bug_titles = " ".join(b.get("title", "").lower() + " " + b.get("detail", "").lower() for b in bugs)
    all_smells = " ".join(s.lower() for s in code_smells)

    if "sql" in sec_titles or "injection" in sec_titles:
        practices.append("Use parameterized queries or an ORM query builder instead of string formatting for database operations.")
    if "secret" in sec_titles or "password" in sec_titles or "key" in sec_titles:
        practices.append("Load API keys and sensitive credentials from environment variables or a secure secrets manager.")
    if "command" in sec_titles or "exec" in sec_titles or "system" in sec_titles:
        practices.append("Avoid executing raw shell commands; use structured APIs and validate all input parameters against an allow-list.")
    if "crypto" in sec_titles or "md5" in sec_titles or "sha1" in sec_titles or "des" in sec_titles:
        practices.append("Use modern cryptographic algorithms (e.g. SHA-256 for hashing, bcrypt/Argon2 for passwords).")
    if "xss" in sec_titles or "html" in sec_titles:
        practices.append("Contextually sanitize and encode all user-supplied input before rendering it in response views.")
    
    if "bare except" in bug_titles or "empty catch" in bug_titles or "except" in bug_titles:
        practices.append("Catch specific exception classes and log meaningful diagnostic details rather than suppressing errors.")
    if "mutable default" in bug_titles:
        practices.append("Default mutable function arguments to `None` and instantiate lists/dicts inside the function body.")
    if "nesting" in bug_titles or "nesting" in all_smells:
        practices.append("Use guard clauses and early returns to reduce cyclomatic nesting and simplify control flow.")
    if "parameter" in bug_titles or "long function" in bug_titles or "long method" in bug_titles:
        practices.append("Decompose long functions into modular, single-responsibility helpers and group related parameters into objects.")
    if "global" in bug_titles or "global" in all_smells:
        practices.append("Avoid mutable global state; pass required dependencies explicitly to functions and classes.")

    # Language-specific additions
    if language == "Python":
        practices.append("Leverage type annotations and context managers (`with` statements) for robust resource management.")
    elif language == "Java":
        practices.append("Use try-with-resources for AutoCloseable resources and favor immutable data structures where possible.")
    elif language in ("JavaScript", "TypeScript"):
        practices.append("Use strict equality (`===`) and enforce TypeScript types for end-to-end data contracts.")
    else:
        practices.append("Follow standard language idioms and maintain comprehensive unit test coverage.")

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for p in practices:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped[:5]


def _dynamic_performance_tips(language: str, bugs: list[dict], security_issues: list[dict],
                              code_smells: list[str], radon_data: dict | None) -> list[str]:
    tips = []
    sec_text = " ".join(i.get("title", "").lower() for i in security_issues)
    bug_text = " ".join(b.get("title", "").lower() for b in bugs)

    if "sql" in sec_text or "database" in sec_text:
        tips.append("Batch database calls where possible and ensure appropriate indexing to prevent N+1 query bottlenecks.")
    
    avg_cc = (radon_data or {}).get("avg_cyclomatic_complexity", 1)
    if avg_cc > 5 or "nesting" in bug_text or "long" in bug_text:
        tips.append("Refactor high-complexity branching and cache repeated computationally expensive lookups.")
    
    if language == "Python":
        tips.append("Use generators, list comprehensions, and built-in algorithms for memory-efficient data processing.")
    elif language == "Java":
        tips.append("Use `StringBuilder` for sequential string manipulations and select optimized Collections based on access patterns.")
    else:
        tips.append("Avoid redundant object allocations and deep copies in performance-critical execution paths.")

    tips.append("Utilize connection pooling and asynchronous I/O where applicable to maximize throughput.")

    seen = set()
    deduped = []
    for t in tips:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped[:4]


def summarize_local(filename: str | None, language: str, bugs: list[dict], security_issues: list[dict],
                     code_smells: list[str], radon_data: dict | None = None) -> dict:
    security_score = _score(security_issues)
    quality_score = _score(bugs) - min(20, len([s for s in code_smells if s != "No significant code smells detected."]) * 4)
    quality_score = max(0, min(100, quality_score))

    if radon_data and radon_data.get("maintainability_index") is not None:
        maintainability_score = max(0, min(100, round(radon_data["maintainability_index"])))
        avg_cc = radon_data.get("avg_cyclomatic_complexity", 1)
        complexity = "Low" if avg_cc <= 5 else "Medium" if avg_cc <= 10 else "High"
    else:
        maintainability_score = max(0, round((security_score + quality_score) / 2) - (5 if len(code_smells) > 3 else 0))
        complexity = None

    has_critical = any(i.get("severity") == "Critical" for i in security_issues)
    has_high = any(i.get("severity") == "High" for i in security_issues + bugs)

    if complexity is None:
        complexity = "High" if (has_critical or security_score < 40) else \
                     "Medium" if (has_high or security_score < 70 or quality_score < 60) else "Low"

    if has_critical or security_score < 40:
        verdict = "Block"
    elif has_high or security_score < 70 or quality_score < 60:
        verdict = "Request changes"
    elif security_issues or bugs or (code_smells and code_smells != ["No significant code smells detected."]):
        verdict = "Approve with suggestions"
    else:
        verdict = "Approve"

    n_sec, n_bugs = len(security_issues), len(bugs)
    parts = [f"Analyzed {filename or 'submitted code'} ({language})."]
    if n_sec:
        top = max(security_issues, key=lambda i: SEVERITY_WEIGHT.get(i.get("severity", "Low"), 0))
        parts.append(f"Found {n_sec} security issue(s), most notably {top['title']} ({top['severity']}, {top.get('owasp_category','-')}).")
    else:
        parts.append("No OWASP-standard security issues were flagged.")
    if n_bugs:
        parts.append(f"The Code Analysis Agent flagged {n_bugs} structural issue(s).")
    if code_smells and code_smells != ["No significant code smells detected."]:
        parts.append(f"Code smells: {', '.join(code_smells[:3])}.")
    summary = " ".join(parts)

    best_practices = _dynamic_best_practices(language, bugs, security_issues, code_smells)
    performance = _dynamic_performance_tips(language, bugs, security_issues, code_smells, radon_data)

    return {
        "summary": summary,
        "pr_verdict": verdict,
        "metrics": {
            "security_score": security_score,
            "quality_score": quality_score,
            "maintainability_score": maintainability_score,
            "complexity": complexity,
        },
        "best_practices": best_practices,
        "performance": performance,
    }


def summarize(code: str, filename: str | None, language: str, bugs: list[dict],
              security_issues: list[dict], code_smells: list[str],
              radon_data: dict | None = None) -> dict:
    """PR Summary Agent entrypoint: uses Gemini LLM when reachable, falls back to dynamic local summarizer."""
    local_baseline = summarize_local(filename, language, bugs, security_issues, code_smells, radon_data)
    try:
        findings_context = {
            "filename": filename or "submitted code",
            "language": language,
            "security_issues": [{"title": s["title"], "severity": s["severity"], "category": s.get("owasp_category", "")} for s in security_issues],
            "bugs": [{"title": b["title"], "severity": b["severity"], "detail": b.get("detail", "")} for b in bugs],
            "code_smells": code_smells,
            "metrics": local_baseline["metrics"],
        }
        prompt = (
            f"Review Summary Request for {filename or 'submitted snippet'} ({language}).\n"
            f"Context and Findings:\n{json.dumps(findings_context, indent=2)}\n\n"
            f"Original Code Context:\n{code[:4000]}\n\n"
            f"Generate a comprehensive review summary. Return a strict JSON object with this exact schema:\n"
            f'{{"summary": "A concise executive summary paragraph explaining what the code does and summarizing key findings",\n'
            f' "pr_verdict": "Approve|Approve with suggestions|Request changes|Block",\n'
            f' "best_practices": ["3-5 context-specific best practice recommendations tailored to this code and language"],\n'
            f' "performance": ["2-4 context-specific performance suggestions tailored to this code"]}}'
        )
        raw = generate(prompt, system="You are a senior lead software architect and code reviewer. Return only valid JSON.")
        parsed = extract_json(raw)
        if isinstance(parsed, dict):
            summary = parsed.get("summary") or local_baseline["summary"]
            pr_verdict = parsed.get("pr_verdict") or local_baseline["pr_verdict"]
            best_practices = parsed.get("best_practices") if isinstance(parsed.get("best_practices"), list) and parsed.get("best_practices") else local_baseline["best_practices"]
            performance = parsed.get("performance") if isinstance(parsed.get("performance"), list) and parsed.get("performance") else local_baseline["performance"]
            return {
                "summary": summary,
                "pr_verdict": pr_verdict,
                "metrics": local_baseline["metrics"],
                "best_practices": best_practices,
                "performance": performance,
            }
        return local_baseline
    except (LLMUnavailable, Exception):
        return local_baseline
