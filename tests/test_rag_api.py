"""IntelliSafe-RAG API tests (orchestrator must be running on :8765)."""
from __future__ import annotations

import os

import httpx
import pytest

BASE = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8765")
TIMEOUT = 60.0


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE, timeout=TIMEOUT) as c:
        health = c.get("/health")
        if health.status_code != 200:
            pytest.skip(f"orchestrator not reachable at {BASE}")
        yield c


def test_rag_ingest_and_query(client: httpx.Client) -> None:
    ingest = client.post("/rag/ingest", json={"source": "directory"})
    ingest.raise_for_status()
    body = ingest.json()
    assert body["ok"] is True
    assert body["data"]["nodes"] >= 1

    query = client.post(
        "/rag/query",
        json={"question": "种草视频开场钩子怎么写？", "mode": "auto"},
    )
    query.raise_for_status()
    qbody = query.json()
    assert qbody["ok"] is True
    assert qbody["data"]["response"]


def test_rag_compliance_check(client: httpx.Client) -> None:
    resp = client.post(
        "/rag/check",
        json={"text": "本产品第一最好，联系手机13800138000"},
    )
    resp.raise_for_status()
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["passed"] is False


def test_l8_metrics_write(client: httpx.Client) -> None:
    resp = client.post(
        "/modules/l8-analytics/metrics",
        json={
            "job_id": "pytest-job",
            "clicks": 100,
            "unique_clicks": 80,
            "conversions": 10,
            "orders": 5,
            "gmv": 1500.0,
        },
    )
    resp.raise_for_status()
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["backend"] in ("sqlite", "postgres")
