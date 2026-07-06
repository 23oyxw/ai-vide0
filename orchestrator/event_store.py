from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple, List
from datetime import datetime, timezone

from orchestrator.config import settings


EVENTS_DIR = settings.jobs_dir / "events"
EVENTS_DIR.mkdir(parents=True, exist_ok=True)


def _event_file(job_id: str) -> Path:
    return EVENTS_DIR / f"{job_id}.ndjson"


def append_event(job_id: str, event: str, data: dict[str, Any]) -> None:
    path = _event_file(job_id)
    payload = {"event": event, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def get_events(job_id: str) -> List[dict[str, Any]]:
    path = _event_file(job_id)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            lines = [line.strip() for line in fh.readlines() if line.strip()]
        return [json.loads(l) for l in lines]
    except Exception:
        return []


def tail_events(job_id: str, since_index: int) -> Tuple[List[dict[str, Any]], int]:
    events = get_events(job_id)
    return events[since_index:], len(events)
