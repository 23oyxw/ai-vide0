"""FastAPI TestClient integration tests — drives the actual app in-process.

Run these with:
    cd C:\\Users\\oyxw\\Projects\\ai-video-orchestrator
    python -m pytest tests/test_integration_api.py -v -x

Requires the orchestrator dependencies installed (not mocked).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(patch_settings) -> TestClient:
    """Create a FastAPI TestClient once per module (shared across tests)."""
    from orchestrator.main import app
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════════════════
# Health & Infrastructure
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoints:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["status"] == "ok"
        assert "L1" in body["data"]["layers"]
        assert "meta" in body

    def test_modules_lists_all(self, client):
        resp = client.get("/modules")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "M1" in body["data"]

    def test_layers_return_registry(self, client):
        resp = client.get("/layers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "L1" in body["data"]
        assert "L8" in body["data"]

    def test_tools_check(self, client):
        resp = client.get("/tools/check")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "video_factory" in body["data"]
        assert "ai_koubo" in body["data"]
        assert "c4d" in body["data"]
        assert "ffmpeg" in body["data"]


# ═══════════════════════════════════════════════════════════════════════════════
# L1 Crawler Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestL1Endpoints:
    def test_search_topics(self, client):
        resp = client.post(
            "/modules/l1-crawler/search",
            json={"keyword": "防晒", "vertical": "电商"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["topics"]) >= 1

    def test_search_topics_with_product_url(self, client):
        resp = client.post(
            "/modules/l1-crawler/search",
            json={
                "keyword": "护肤",
                "vertical": "电商",
                "product_url": "https://example.com/p/demo",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["crawl"] is not None

    def test_list_topics(self, client):
        resp = client.get("/modules/l1-crawler/topics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert isinstance(body["data"]["topics"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# L2 Content Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestL2Endpoints:
    def test_generate_script(self, client):
        resp = client.post(
            "/modules/l2-content/generate-script",
            json={"topic": "防晒好物", "product_url": "https://e.g/p/1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["script"]["segments"]

    def test_get_script_by_id(self, client):
        # Generate first
        gen = client.post(
            "/modules/l2-content/generate-script",
            json={"topic": "测试商品"},
        )
        sid = gen.json()["data"]["script"]["id"]

        resp = client.get(f"/modules/l2-content/scripts/{sid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["script"]["id"] == sid

    def test_get_script_not_found(self, client):
        resp = client.get("/modules/l2-content/scripts/nonexistent")
        # Should return error envelope
        body = resp.json()
        assert body["ok"] is False or resp.status_code >= 400

    def test_optimize_prompts(self, client):
        resp = client.post(
            "/modules/l2-content/optimize-prompts",
            json={
                "product_url": "https://e.g/p/1",
                "topic": "防晒 · 护肤",
                "product_title": "轻透防晒霜",
                "category": "护肤",
                "pain_points": ["油腻", "过敏"],
                "platform": "抖音/小红书",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["optimized_topic"]
        assert len(body["data"]["hook_suggestions"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# L3 Storyboard Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestL3Endpoints:
    def test_build_storyboard_from_script(self, client):
        # First generate a script
        gen = client.post(
            "/modules/l2-content/generate-script",
            json={"topic": "分镜测试商品"},
        )
        sid = gen.json()["data"]["script"]["id"]

        resp = client.post(
            "/modules/l3-storyboard/build-from-script",
            json={"script_id": sid},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["storyboard"]["id"].startswith("sb")

    def test_get_storyboard_by_id(self, client):
        gen = client.post(
            "/modules/l2-content/generate-script",
            json={"topic": "查找分镜商品"},
        )
        sid = gen.json()["data"]["script"]["id"]
        sb = client.post(
            "/modules/l3-storyboard/build-from-script",
            json={"script_id": sid},
        )
        sbid = sb.json()["data"]["storyboard"]["id"]

        resp = client.get(f"/modules/l3-storyboard/storyboard/{sbid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["storyboard"]["id"] == sbid


# ═══════════════════════════════════════════════════════════════════════════════
# L5 Job Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestL5Endpoints:
    def test_create_job(self, client):
        resp = client.post(
            "/modules/l5-scheduler/jobs",
            json={"product_url": "https://e.g/p/job", "layers": ["L1", "L2"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["job"]["status"] == "pending"

    def test_list_jobs(self, client):
        # Create one first
        client.post(
            "/modules/l5-scheduler/jobs",
            json={"product_url": "https://e.g/p/list"},
        )
        resp = client.get("/modules/l5-scheduler/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["total"] >= 1

    def test_get_job_status(self, client):
        created = client.post(
            "/modules/l5-scheduler/jobs",
            json={"product_url": "https://e.g/p/status"},
        )
        jid = created.json()["data"]["job"]["job_id"]
        resp = client.get(f"/jobs/{jid}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["job_id"] == jid


# ═══════════════════════════════════════════════════════════════════════════════
# L6 QA Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestL6Endpoints:
    def test_get_rules(self, client):
        resp = client.get("/modules/l6-qa/rules")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["prohibited_words"]) > 0

    def test_validate_content(self, client):
        resp = client.post(
            "/modules/l6-qa/validate",
            json={"script_text": "这是一段合规安全的种草文案"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "passed" in body["data"]


# ═══════════════════════════════════════════════════════════════════════════════
# L7 Publish Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestL7Endpoints:
    def test_publish(self, client):
        resp = client.post(
            "/modules/l7-publish/publish",
            json={
                "job_id": "test-pub-api",
                "video_path": "/tmp/fake.mp4",
                "title": "种草视频",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["published"]["id"].startswith("pub")

    def test_list_published(self, client):
        resp = client.get("/modules/l7-publish/published")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert isinstance(body["data"]["items"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# L8 Analytics Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestL8Endpoints:
    def test_dashboard(self, client):
        resp = client.get("/modules/l8-analytics/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["job_count"] >= 0
        assert "chart" in body["data"]

    def test_metrics_upsert(self, client):
        resp = client.post(
            "/modules/l8-analytics/metrics",
            json={
                "job_id": "api-test-l8",
                "clicks": 500,
                "unique_clicks": 400,
                "conversions": 25,
                "orders": 12,
                "gmv": 2400.0,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["backend"] in ("sqlite", "postgres")

    def test_click_data(self, client):
        resp = client.get("/modules/l8-analytics/click?job_id=api-test-l8")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["clicks"] >= 0

    def test_conversion_data(self, client):
        resp = client.get("/modules/l8-analytics/conversion")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True

    def test_order_data(self, client):
        resp = client.get("/modules/l8-analytics/order")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True

    def test_analysis(self, client):
        resp = client.get("/modules/l8-analytics/analysis?job_id=api-test-l8")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["optimization_hints"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineEndpoint:
    def test_run_full_pipeline(self, client):
        resp = client.post(
            "/pipeline/run",
            json={
                "product_url": "https://example.com/product/demo",
                "demo_name": "post_production_15s_zhongcao",
                "layers": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
                "topic": "测试管线全流程",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["meta"]["job_id"]
        assert len(body["data"]["layer_results"]) == 8
        assert body["data"]["status"] == "ok"

    def test_run_partial_pipeline(self, client):
        resp = client.post(
            "/pipeline/run",
            json={
                "product_url": "https://example.com/product/demo",
                "layers": ["L1", "L2", "L3"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["layer_results"]) == 3

    def test_pipeline_force_qa_fail(self, client):
        resp = client.post(
            "/pipeline/run",
            json={
                "layers": ["L1", "L2", "L3", "L4", "L5", "L6"],
                "force_qa_fail": True,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "qa_failed"
        assert body["data"]["retry_from"] == "L2"

    def test_pipeline_rejects_bad_layer_order(self, client):
        resp = client.post(
            "/pipeline/run",
            json={"layers": ["L3", "L1"]},
        )
        body = resp.json()
        assert body["ok"] is False
        assert "Layer order violation" in body["error"]["message"]

    def test_pipeline_rejects_unknown_layer(self, client):
        resp = client.post(
            "/pipeline/run",
            json={"layers": ["L1", "L99"]},
        )
        body = resp.json()
        assert body["ok"] is False
        assert "Unknown layer" in body["error"]["message"]


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGEndpoints:
    def test_rag_status(self, client):
        resp = client.get("/rag/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "knowledge_dir" in body["data"]

    def test_rag_ingest_and_query(self, client):
        ingest = client.post("/rag/ingest", json={"source": "directory"})
        assert ingest.status_code == 200
        assert ingest.json()["ok"] is True

        query = client.post(
            "/rag/query",
            json={"question": "种草视频开场钩子怎么写？", "mode": "auto"},
        )
        assert query.status_code == 200
        qbody = query.json()
        assert qbody["ok"] is True
        assert qbody["data"]["response"]

    def test_rag_compliance_check(self, client):
        resp = client.post(
            "/rag/check",
            json={"text": "本产品第一最好，联系手机13800138000"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["passed"] is False

    def test_rag_query_kg(self, client):
        client.post("/rag/ingest", json={"source": "directory"})
        resp = client.post(
            "/rag/query",
            json={"question": "种草", "mode": "kg"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_rag_cost_estimate(self, client):
        resp = client.post(
            "/rag/estimate-cost",
            json={"source": "texts", "texts": ["hello world " * 100]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["estimated_chunks"] >= 1

    def test_rag_report(self, client):
        resp = client.post(
            "/report",
            json={"question": "分析总体表现", "job_id": "api-test-report"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Webhook Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebhookEndpoints:
    def test_webhook_render(self, client):
        resp = client.post(
            "/webhooks/render",
            json={
                "job_id": "webhook-test-01",
                "status": "completed",
                "artifact_url": "https://blob.example.com/video/final.mp4",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["acknowledged"] is True

    def test_webhook_analytics(self, client):
        resp = client.post(
            "/webhooks/analytics",
            json={
                "job_id": "webhook-test-01",
                "metric_date": "2026-07-05",
                "clicks": 1200,
                "unique_clicks": 900,
                "conversions": 54,
                "orders": 28,
                "gmv": 5566.0,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["backend"] in ("sqlite", "postgres")

    def test_webhook_analytics_with_minimal_payload(self, client):
        resp = client.post(
            "/webhooks/analytics",
            json={"job_id": "minimal", "clicks": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
