"""RAG 问答 smoke test — 需 orchestrator 在 :8765 运行。"""
from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8765")


def test_rag_query() -> None:
    with httpx.Client(timeout=30.0) as client:
        ingest = client.post(f"{BASE}/rag/ingest", json={"source": "directory"})
        ingest.raise_for_status()
        assert ingest.json().get("ok") is True

        query = client.post(
            f"{BASE}/rag/query",
            json={"question": "种草视频开场钩子怎么写？", "mode": "auto"},
        )
        query.raise_for_status()
        body = query.json()
        assert body.get("ok") is True
        assert body.get("data", {}).get("response")


if __name__ == "__main__":
    try:
        test_rag_query()
        print("test_query OK")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
