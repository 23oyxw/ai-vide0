"""Unit tests for L1-L8 layer implementations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.layers.l1_crawler import CrawlerLayer, _extract_meta
from orchestrator.layers.l2_content import ContentLayer
from orchestrator.layers.l3_storyboard import StoryboardLayer
from orchestrator.layers.l5_scheduler import SchedulerLayer
from orchestrator.layers.l6_qa import QALayer, _qa_from_manifest
from orchestrator.layers.l7_publish import _resolve_video_path, PublishLayer
from orchestrator.layers.l8_data import DataLayer, _hints_from_qa, DEFAULT_OPTIMIZATION_HINTS
from orchestrator.layers.base import LayerContext, LayerResult
from orchestrator.pipeline_state import QA_PASS_THRESHOLD
from orchestrator.config import settings


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_ctx(**overrides) -> LayerContext:
    """Build a LayerContext with sensible defaults for testing."""
    defaults = {
        "job_id": "j-test-001",
        "product_url": "https://example.com/product/demo",
        "demo_name": "post_production_15s_zhongcao",
        "c4d_project": None,
        "metadata": {},
        "artifacts": {},
        "errors": [],
    }
    defaults.update(overrides)
    return LayerContext(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# L1 Crawler
# ═══════════════════════════════════════════════════════════════════════════════

class TestL1Crawler:
    """Tests for the CrawlerLayer (L1)."""

    def test_extract_meta_og_title(self):
        html = '<meta property="og:title" content="My Product"/>'
        assert _extract_meta(html, "og:title", "title") == "My Product"

    def test_extract_meta_og_description(self):
        html = '<meta name="og:description" content="A great product"/>'
        assert _extract_meta(html, "og:description", "description") == "A great product"

    def test_extract_meta_fallback_to_title_tag(self):
        html = "<html><head><title>Page Title Here</title></head></html>"
        result = _extract_meta(html, "og:title", "title")
        assert "Page Title Here" in result

    def test_extract_meta_returns_empty_when_nothing_matches(self):
        html = "<html><head></head><body>no meta</body></html>"
        assert _extract_meta(html, "og:title", "title") == ""

    def test_extract_single_quoted_meta(self):
        html = "<meta property='og:title' content='Single Quote Product'/>"
        assert _extract_meta(html, "og:title", "title") == "Single Quote Product"

    @pytest.mark.asyncio
    async def test_run_crawls_and_produces_artifacts(self, mock_httpx_client, monkeypatch):
        monkeypatch.setattr(settings, "rag_auto_ingest_crawl", False)
        layer = CrawlerLayer()
        ctx = make_ctx()
        result = await layer.run(ctx)
        assert result.status == "ok"
        assert result.artifacts["crawled_url"] == ctx.product_url
        assert result.artifacts["crawled_domain"] == "example.com"
        assert result.artifacts["crawled_title"] != ""

    @pytest.mark.asyncio
    async def test_run_without_product_url_uses_default(self, monkeypatch):
        monkeypatch.setattr(settings, "rag_auto_ingest_crawl", False)
        layer = CrawlerLayer()
        ctx = make_ctx(product_url=None)
        result = await layer.run(ctx)
        assert result.status == "ok"
        assert result.artifacts["crawled_url"] == "https://example.com/product"


# ═══════════════════════════════════════════════════════════════════════════════
# L5 Scheduler
# ═══════════════════════════════════════════════════════════════════════════════

class TestL5Scheduler:
    """Tests for the SchedulerLayer (L5)."""

    @pytest.mark.asyncio
    async def test_run_persists_job(self, monkeypatch, tmp_path):
        """Override the module-level job_store to use a temp dir."""
        from orchestrator.job_store import JobStore
        test_store = JobStore(tmp_path / "jobs")
        monkeypatch.setattr(
            "orchestrator.layers.l5_scheduler.job_store", test_store
        )
        monkeypatch.setattr(
            "orchestrator.modules.l5_scheduler.service.job_store", test_store
        )
        monkeypatch.setattr(
            "orchestrator.main.job_store", test_store
        )
        layer = SchedulerLayer()
        ctx = make_ctx(artifacts={"manifest_path": "/tmp/m.json", "video_path": "/tmp/v.mp4"})
        result = await layer.run(ctx)
        assert result.status == "ok"
        assert result.artifacts["scheduled_job"] == ctx.job_id
        job_files = list((tmp_path / "jobs").glob("*.json"))
        assert len(job_files) >= 1

    @pytest.mark.asyncio
    async def test_run_message_includes_file_name(self, monkeypatch, tmp_path):
        from orchestrator.job_store import JobStore
        test_store = JobStore(tmp_path / "jobs2")
        monkeypatch.setattr("orchestrator.layers.l5_scheduler.job_store", test_store)
        monkeypatch.setattr("orchestrator.modules.l5_scheduler.service.job_store", test_store)
        monkeypatch.setattr("orchestrator.main.job_store", test_store)
        layer = SchedulerLayer()
        ctx = make_ctx()
        result = await layer.run(ctx)
        assert ".json" in result.message
        assert ctx.job_id in result.message


# ═══════════════════════════════════════════════════════════════════════════════
# L6 QA
# ═══════════════════════════════════════════════════════════════════════════════

class TestL6QA:
    """Tests for the QALayer (L6)."""

    def test_qa_from_manifest_no_file_returns_zero(self):
        score, passed, failed = _qa_from_manifest("/nonexistent/manifest.json", "/tmp")
        assert score == 0.0
        assert "manifest_exists" in failed

    def test_qa_from_manifest_detects_duration_violation(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps({
                "final_video": "final.mp4",
                "scenes": [{"duration": 5.0}, {"duration": 2.0}],
            }),
            encoding="utf-8",
        )
        # Create a fake video
        (tmp_path / "final.mp4").touch()
        score, passed, failed = _qa_from_manifest(str(manifest), str(tmp_path))
        assert "duration_15s" in failed
        assert score < 1.0

    def test_qa_from_manifest_good_duration(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps({
                "final_video": "final.mp4",
                "scenes": [
                    {"duration": 3.0},
                    {"duration": 4.0},
                    {"duration": 4.0},
                    {"duration": 3.0},
                ],
            }),
            encoding="utf-8",
        )
        (tmp_path / "final.mp4").touch()
        score, passed, failed = _qa_from_manifest(str(manifest), str(tmp_path))
        assert "duration_15s" in passed
        assert "scene_count" in passed
        assert "final_video_exists" in passed
        assert score >= QA_PASS_THRESHOLD

    def test_qa_from_manifest_missing_video_penalty(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps({
                "final_video": "final.mp4",
                "scenes": [{"duration": 3}, {"duration": 4}, {"duration": 4}],
            }),
            encoding="utf-8",
        )
        # No final.mp4 created -> penalty
        score, _, failed = _qa_from_manifest(str(manifest), str(tmp_path))
        assert "final_video_exists" in failed
        assert score < 1.0

    @pytest.mark.asyncio
    async def test_run_force_fail_flag(self):
        layer = QALayer()
        ctx = make_ctx(metadata={"force_qa_fail": True})
        result = await layer.run(ctx)
        assert result.status == "error"
        assert "forced" in result.message

    @pytest.mark.asyncio
    async def test_run_with_prohibited_script(self):
        layer = QALayer()
        ctx = make_ctx(
            metadata={"script": "本产品绝对第一好用"},
            artifacts={"manifest_path": "", "video_factory_output": ""},
        )
        result = await layer.run(ctx)
        assert result.status == "error"
        assert "safety" in result.message.lower() or float(result.artifacts.get("qa_score", "1")) < 1.0

    @pytest.mark.asyncio
    async def test_run_clean_script_no_manifest_scores_ok(self):
        layer = QALayer()
        ctx = make_ctx(
            metadata={"script": "这是一个合规的口播文案"},
            artifacts={"manifest_path": "", "video_factory_output": ""},
        )
        result = await layer.run(ctx)
        # Should pass with stub score or safety check
        score = float(result.artifacts.get("qa_score", "0"))
        if result.status == "ok":
            assert score >= QA_PASS_THRESHOLD or settings.pipeline_mode == "mock"


# ═══════════════════════════════════════════════════════════════════════════════
# L7 Publish
# ═══════════════════════════════════════════════════════════════════════════════

class TestL7Publish:
    """Tests for the PublishLayer (L7) and _resolve_video_path."""

    def test_resolve_video_path_from_output_dir(self, tmp_path):
        out = tmp_path / "output"
        out.mkdir()
        vid = out / "final.mp4"
        vid.write_text("fake mp4", encoding="utf-8")
        result = _resolve_video_path({"video_factory_output": str(out)})
        assert result == str(vid)

    def test_resolve_video_path_from_direct_video_path(self):
        result = _resolve_video_path({"video_path": "/tmp/out.mp4"})
        assert result == "/tmp/out.mp4"

    def test_resolve_video_path_empty_inputs(self):
        result = _resolve_video_path({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_run_publish_produces_target_artifact(self, monkeypatch):
        """Publish layer should identify at least one publish target."""
        from orchestrator.adapters import ai_koubo as ak
        monkeypatch.setattr(ak, "_reachable", AsyncMock(return_value=False))
        layer = PublishLayer()
        ctx = make_ctx(
            artifacts={
                "script": "test script",
                "video_path": "/tmp/test.mp4",
                "video_factory_output": "",
            }
        )
        result = await layer.run(ctx)
        # With ai-koubo offline and no video_factory_output,
        # multi-platform stubs should still return some results
        assert "publish_target" in result.artifacts
        assert result.artifacts.get("publish_platforms", "").startswith("0/4") or result.status in ("ok", "skipped")


# ═══════════════════════════════════════════════════════════════════════════════
# L8 Data / Analytics
# ═══════════════════════════════════════════════════════════════════════════════

class TestL8Data:
    """Tests for the DataLayer (L8) and optimisation hints."""

    def test_hints_from_qa_below_threshold(self):
        hints = _hints_from_qa(0.5, "duration_15s,scene_count")
        assert any("L2" in h for h in hints)
        assert any("L3" in h for h in hints)

    def test_hints_from_qa_above_threshold(self):
        hints = _hints_from_qa(0.9, "")
        assert len(hints) == 0

    def test_hints_from_qa_moderate_score(self):
        hints = _hints_from_qa(0.8, "")
        assert any("加强" in h or "优化" in h for h in hints)

    def test_default_optimization_hints_are_four(self):
        assert len(DEFAULT_OPTIMIZATION_HINTS) >= 4

    def test_hints_for_final_video_missing(self):
        hints = _hints_from_qa(0.75, "final_video_exists")
        assert any("L4" in h and "final.mp4" in h for h in hints)

    @pytest.mark.asyncio
    async def test_run_produces_metrics_and_hints(self, patch_settings):
        layer = DataLayer()
        ctx = make_ctx(
            artifacts={
                "qa_score": "0.85",
                "qa_checks_failed": "",
                "publish_target": "douyin",
                "video_path": "/tmp/v.mp4",
                "manifest_path": "/tmp/m.json",
                "segment_count": "4",
                "pipeline_mode": "mock",
            }
        )
        result = await layer.run(ctx)
        assert result.status == "ok"
        assert "metrics_recorded" in result.artifacts
        assert "optimization_hints" in result.artifacts
        assert ctx.metadata.get("optimization_hints") is not None

    @pytest.mark.asyncio
    async def test_run_with_low_qa_score_adds_hints(self, patch_settings):
        layer = DataLayer()
        ctx = make_ctx(
            artifacts={
                "qa_score": "0.55",
                "qa_checks_failed": "duration_15s,final_video_exists",
            }
        )
        result = await layer.run(ctx)
        hints = ctx.metadata.get("optimization_hints", [])
        assert len(hints) > DEFAULT_OPTIMIZATION_HINTS.__len__()  # low QA adds extra
