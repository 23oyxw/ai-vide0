from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestrator.config import settings


def new_id(prefix: str = "") -> str:
    short = str(uuid.uuid4())[:8]
    return f"{prefix}{short}" if prefix else short


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def module_dir(*parts: str) -> Path:
    root = settings.data_root
    path = root.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_json_records(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    records: list[dict[str, Any]] = []
    for file in sorted(directory.glob("*.json"), reverse=True):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                records.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return records
