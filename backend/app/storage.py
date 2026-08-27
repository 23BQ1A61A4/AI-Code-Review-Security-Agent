"""
Lightweight persistence for the demo: an in-memory dict mirrored to a JSON
file on disk (backend/data/store.json) so submissions survive a server
restart. Good enough for a local project demo; swap for a real database in
production.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STORE_FILE = DATA_DIR / "store.json"

_lock = threading.Lock()
_state: dict[str, dict[str, Any]] = {"submissions": {}, "analyses": {}}


def _load() -> None:
    if STORE_FILE.exists():
        try:
            _state.update(json.loads(STORE_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass


def _save() -> None:
    STORE_FILE.write_text(json.dumps(_state, indent=2), encoding="utf-8")


_load()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def save_submission(record: dict[str, Any]) -> None:
    with _lock:
        _state["submissions"][record["id"]] = record
        _save()


def save_analysis(record: dict[str, Any]) -> None:
    with _lock:
        _state["analyses"][record["id"]] = record
        _save()


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    return _state["analyses"].get(analysis_id)


def list_analyses() -> list[dict[str, Any]]:
    return sorted(_state["analyses"].values(), key=lambda r: r.get("ts", 0), reverse=True)


def now_ms() -> int:
    return int(time.time() * 1000)
