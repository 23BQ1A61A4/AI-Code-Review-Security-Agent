"""
Dynamic Rule and Knowledge Loader.
Loads vulnerability definitions, remediation templates, and report knowledge
from external JSON configuration files rather than hardcoded tables in agent code.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).parent


def _load_json(filename: str) -> Any:
    path = RULES_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def load_security_rules() -> list[tuple[str, str, re.Pattern, str, str, str]]:
    """Dynamically loads security scanning rules from security_rules.json."""
    raw_rules = _load_json("security_rules.json") or []
    compiled = []
    for r in raw_rules:
        flags = re.I if r.get("flags") == "IGNORECASE" else 0
        pattern = re.compile(r["pattern"], flags) if flags else re.compile(r["pattern"])
        compiled.append((
            r["kind"],
            r["title"],
            pattern,
            r["severity"],
            r["owasp_category"],
            r["detail"],
        ))
    return compiled


def load_remediation_data() -> tuple[dict[str, tuple[str, str]], list[tuple[str, str, str]], dict[str, str]]:
    """Dynamically loads remediation templates from remediation_templates.json."""
    data = _load_json("remediation_templates.json") or {}
    sec_raw = data.get("security_templates", {})
    sec_templates = {k: (v["recommendation"], v["corrected_code"]) for k, v in sec_raw.items()}

    bug_raw = data.get("bug_keyword_templates", [])
    bug_templates = [(b["keyword"], b["recommendation"], b["corrected_code"]) for b in bug_raw]

    bandit_map = data.get("bandit_template_map", {})
    return sec_templates, bug_templates, bandit_map


def load_report_knowledge() -> tuple[dict[str, str], dict[str, str], list[tuple[str, str]], list[tuple[str, str]]]:
    """Dynamically loads report knowledge from report_knowledge.json."""
    data = _load_json("report_knowledge.json") or {}
    root_cause = data.get("root_cause", {})
    best_practice = data.get("best_practice", {})
    
    bug_rc_dict = data.get("bug_root_cause", {})
    bug_rc_list = [(k, v) for k, v in bug_rc_dict.items()]

    bug_bp_dict = data.get("bug_best_practice", {})
    bug_bp_list = [(k, v) for k, v in bug_bp_dict.items()]

    return root_cause, best_practice, bug_rc_list, bug_bp_list
