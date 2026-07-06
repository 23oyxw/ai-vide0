"""Shared fixtures and configuration for the AI Video Orchestrator test suite."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Path helpers ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_root() -> Path:
    """Absolute path to the tests directory."""
    return Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the ai-video-orchestrator root."""
    return test_root().parent


# ── Temporary directories ──────────────────────────────────────────────────────

@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Scratch data directory for job stores, L8 DB, etc."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def tmp_jobs_dir(tmp_data_dir: Path) -> Path:
    """Scratch jobs directory."""
    d = tmp_data_dir / "jobs"
    d.mkdir()
    return d


@pytest.fixture
def tmp_knowledge_dir(tmp_data_dir: Path) -> Path:
    """Scratch RAG knowledge directory seeded with one markdown file."""
    d = tmp_data_dir / "knowledge"
    d.mkdir(parents=True)
    (d / "test_kb.md").write_text(
        "# 种草指南\n\n1. 前三秒钩子决定完播率\n2. CTA 必须清晰可点击\n"
        "3. 口播长度建议控制在 50 字以内\n4. 产品特写镜头至少 3 秒\n"
        "5. 避免使用广告法违规词汇，使用\"优选\"\"推荐\"\"人气\"等合规表达\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def tmp_rag_cache_dir(tmp_data_dir: Path) -> Path:
    d = tmp_data_dir / "rag_cache"
    d.mkdir(parents=True)
    return d


# ── Sample data ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_product_url() -> str:
    return "https://example.com/product/demo"


@pytest.fixture
def sample_pipeline_request() -> dict:
    return {
        "product_url": "https://example.com/product/demo",
        "demo_name": "post_production_15s_zhongcao",
        "layers": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
        "topic": "防晒好物",
        "script": "",
    }


@pytest.fixture
def sample_script_text() -> str:
    return (
        "还在纠结防晒怎么选？今天带你看这款平价好物。"
        "质地轻薄不油腻，SPF50+ 日常完全够用。"
        "实拍上手，水感清透，成膜快不泛白。"
        "链接放评论区了，限时福利别错过。"
    )


@pytest.fixture
def sample_script_with_prohibited() -> str:
    return "本产品绝对第一，全球首发，100%纯天然无副作用，联系手机13800138000"


@pytest.fixture
def sample_job_state() -> dict:
    return {
        "status": "running",
        "pipeline_status": "running",
        "product_url": "https://example.com/product/demo",
        "demo_name": "post_production_15s_zhongcao",
        "script_id": "s12345678",
        "storyboard_id": "sb12345678",
        "render_job_id": "r12345678",
        "manifest_path": "",
        "video_path": "",
        "qa_score": "0.85",
        "publish_target": "",
        "retry_count": 0,
        "errors": [],
        "created_at": "2026-07-05T00:00:00.000Z",
        "updated_at": "2026-07-05T00:00:00.000Z",
    }


@pytest.fixture
def sample_l1_topics() -> list[dict]:
    return [
        {"keyword": "夏季防晒", "heat": 9200, "vertical": "电商", "source": "curated"},
        {"keyword": "平价护肤", "heat": 8800, "vertical": "电商", "source": "curated"},
        {"keyword": "户外装备", "heat": 6900, "vertical": "电商", "source": "curated"},
    ]


# ── Mock helpers ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_httpx_client():
    """Return a mock httpx.AsyncClient that returns fake HTML with OG tags."""
    with patch("httpx.AsyncClient") as mock_cls:
        client = MagicMock()
        mock_cls.return_value.__aenter__.return_value = client

        async def fake_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.text = (
                '<html><head>'
                '<meta property="og:title" content="Test Product Title"/>'
                '<meta property="og:description" content="A great demo product"/>'
                '<meta property="og:image" content="https://img.example.com/p1.jpg"/>'
                '<title>Page Title</title>'
                '</head><body><h1>Product Page</h1></body></html>'
            )
            return resp

        client.get = fake_get
        client.post = AsyncMock(return_value=MagicMock(status_code=200, text="{}"))
        yield client


@pytest.fixture
def patch_settings(monkeypatch, tmp_data_dir, tmp_jobs_dir, tmp_knowledge_dir, tmp_rag_cache_dir):
    """Patch orchestrator.config.settings for isolated test runs."""
    import orchestrator.config as cfg

    monkeypatch.setattr(cfg.settings, "jobs_dir", tmp_jobs_dir)
    monkeypatch.setattr(cfg.settings, "data_root", tmp_data_dir)
    monkeypatch.setattr(cfg.settings, "rag_knowledge_dir", tmp_knowledge_dir)
    monkeypatch.setattr(cfg.settings, "rag_cache_dir", tmp_rag_cache_dir)
    monkeypatch.setattr(cfg.settings, "rag_chroma_dir", tmp_rag_cache_dir / "chroma_db")
    monkeypatch.setattr(cfg.settings, "pipeline_mode", "mock")
    monkeypatch.setattr(cfg.settings, "rag_auto_ingest_crawl", False)
    monkeypatch.setattr(cfg.settings, "rag_bootstrap_on_startup", False)
    monkeypatch.setattr(cfg.settings, "zhipu_api_key", "")  # block real API calls
    monkeypatch.setattr(cfg.settings, "database_url", "")
    monkeypatch.setattr(cfg.settings, "postgres_url", "")

    # Clear any stale RAG stub index to prevent cross-test contamination
    from orchestrator.rag.indexes import _stub_index
    _stub_index_instance = getattr(
        __import__("orchestrator.rag.indexes", fromlist=["_stub_index"]),
        "_stub_index", None
    )
    from orchestrator.rag.indexes import get_stub_index
    stub = get_stub_index()
    stub.nodes.clear()

    return cfg.settings
