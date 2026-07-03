from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestrator.config import settings


class JobStore:
    """Simple JSON-file job persistence for L5 scheduler."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, job_id: str, state: dict[str, Any]) -> Path:
        payload = dict(state)
        payload["job_id"] = job_id
        payload["updated_at"] = datetime.now(UTC).isoformat()
        path = self.root / f"{job_id}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, job_id: str) -> dict[str, Any] | None:
        path = self.root / f"{job_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_jobs(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))


job_store = JobStore(settings.jobs_dir)
