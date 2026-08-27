"""
Multi-Agent Orchestration and Analysis Pipeline (Milestone 2 + 3).

Runs the Code Analysis Agent and Security Vulnerability Agent in parallel
(as required by Milestone 2), merges their output into a unified findings
list, then runs the Remediation Agent and PR Summary Agent on the merged
result (Milestone 3) to produce the final review payload the frontend
renders.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from . import code_analysis_agent, pr_summary_agent, remediation_agent, security_agent


def run_pipeline(code: str, language: str, filename: str | None) -> dict:
    # --- Milestone 2: Code Analysis Agent + Security Vulnerability Agent in parallel ---
    with ThreadPoolExecutor(max_workers=2) as pool:
        analysis_future = pool.submit(code_analysis_agent.analyze, code, language)
        security_future = pool.submit(security_agent.scan, code, language)
        analysis_result = analysis_future.result()
        security_result = security_future.result()

    bugs = analysis_result.get("bugs", [])
    code_smells = analysis_result.get("code_smells", [])
    radon_data = analysis_result.get("radon")
    security_issues_raw = security_result.get("security_issues", [])
    # strip internal bookkeeping field before it reaches the frontend
    security_issues = [{k: v for k, v in i.items() if k != "kind"} for i in security_issues_raw]

    # --- Milestone 3: Remediation Agent ---
    fixes = remediation_agent.generate_fixes(code, language, bugs, security_issues_raw)

    # --- Milestone 3: PR Summary Agent ---
    summary_result = pr_summary_agent.summarize(
        code, filename, language, bugs, security_issues, code_smells, radon_data
    )

    return {
        "summary": summary_result["summary"],
        "pr_verdict": summary_result["pr_verdict"],
        "metrics": summary_result["metrics"],
        "bugs": bugs,
        "security_issues": security_issues,
        "fixes": fixes,
        "code_smells": code_smells,
        "best_practices": summary_result["best_practices"],
        "performance": summary_result["performance"],
        "engines": {
            "code_analysis": analysis_result.get("engine", "unknown"),
            "security_scan": security_result.get("engine", "unknown"),
        },
    }
