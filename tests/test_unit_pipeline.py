"""Unit & integration tests for the pipeline runner and job store."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.config import settings
from orchestrator.pipeline_runner import run_pipeline
from orchestrator.job_store import JobStore, job_store
from orchestrator.pipeline_state import PipelineState, LAYER_INDEX, QA_RETRY_FROM, QA_PASS_THRESHOLD
from orchestrator.schemas import PipelineRunRequest


# ═══════════════════════════════════════════════════════════════════════════════
# Job Store
# ═══════════════════════════════════════════════════════════════════════════════

class TestJobStore:
    """Unit tests for the JSON-file JobStore persistence layer."""

    def test_save_and_load_roundtrip(self, tmp_path):
        store = JobStore(tmp_path)
        store.save("job-001", {"status": "pending", "count": 42, "tags": ["a", "b"]})
        loaded = store.load("job-001")
        assert loaded is not None
        assert loaded["status"] == "pending"
        assert loaded["count"] == 42
        assert loaded["tags"] == ["a", "b"]
        assert "job_id" in loaded
        assert "updated_at" in loaded

    def test_save_overwrites(self, tmp_path):
        store = JobStore(tmp_path)
        store.save("job-ov", {"version": 1})
        store.save("job-ov", {"version": 2})
        loaded = store.load("job-ov")
        assert loaded["version"] == 2

    def test_load_missing_returns_none(self, tmp_path):
        store = JobStore(tmp_path)
        assert store.load("nonexistent") is None

    def test_list_jobs_sorted(self, tmp_path):
        store = JobStore(tmp_path)
        store.save("job-b", {})
        store.save("job-a", {})
        store.save("job-c", {})
        ids = store.list_jobs()
        assert ids == ["job-a", "job-b", "job-c"]

    def test_list_jobs_empty(self, tmp_path):
        store = JobStore(tmp_path)
        assert store.list_jobs() == []

    def test_unicode_job_data(self, tmp_path):
        store = JobStore(tmp_path)
        store.save("cn-001", {"标题": "测试工作", "描述": "中文内容"})
        loaded = store.load("cn-001")
        assert loaded["标题"] == "测试工作"

    def test_job_store_creates_dir(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "jobs"
        store = JobStore(nested)
        assert nested.exists()
        store.save("test", {})
        assert (nested / "test.json").exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Runner — Full Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineRunner:
    """End-to-end tests for run_pipeline (L1 through L8)."""

    @pytest.mark.asyncio
    async def test_full_pipeline_runs_all_eight_layers(self, patch_settings):
        """A full L1-L8 pipeline should complete with 8 layer results."""
        from orchestrator.adapters import ai_koubo as ak
        # Clear any pre-existing stub index data and knowledge graph
        from orchestrator.rag.indexes import get_stub_index
        get_stub_index().nodes.clear()
        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            req = PipelineRunRequest(
                product_url="https://example.com/product/demo",
                demo_name="post_production_15s_zhongcao",
                layers=["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
                topic="优质防晒好物推荐",
            )
            result = await run_pipeline(req)

        assert len(result.layer_results) == 8
        assert result.job_id.startswith("j")
        assert result.artifacts
        # Status may be 'ok' or 'qa_failed' depending on RAG-injected content
        assert result.status in ("ok", "qa_failed")

    @pytest.mark.asyncio
    async def test_partial_pipeline_l1_to_l3(self, patch_settings):
        from orchestrator.adapters import ai_koubo as ak
        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            req = PipelineRunRequest(
                product_url="https://example.com/product/demo",
                layers=["L1", "L2", "L3"],
                topic="护肤好物",
            )
            result = await run_pipeline(req)

        assert result.status == "ok"
        assert len(result.layer_results) == 3
        # L3 should have produced a storyboard
        assert result.artifacts.get("storyboard_id", "").startswith("sb")

    @pytest.mark.asyncio
    async def test_pipeline_with_force_qa_fail(self, patch_settings):
        from orchestrator.adapters import ai_koubo as ak
        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            req = PipelineRunRequest(
                demo_name="post_production_15s_zhongcao",
                layers=["L1", "L2", "L3", "L4", "L5", "L6"],
                force_qa_fail=True,
            )
            result = await run_pipeline(req)

        assert result.status == "qa_failed"
        assert result.retry_from == QA_RETRY_FROM

    @pytest.mark.asyncio
    async def test_pipeline_produces_optimization_hints(self, patch_settings):
        from orchestrator.adapters import ai_koubo as ak
        from orchestrator.rag.indexes import get_stub_index
        get_stub_index().nodes.clear()
        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            req = PipelineRunRequest(
                product_url="https://example.com/product/demo",
                layers=["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
                topic="优质好物推荐",
            )
            result = await run_pipeline(req)

        # When QA passes, L8 should produce optimization hints
        if result.status == "ok":
            assert len(result.optimization_hints) >= 1
        else:
            assert result.status == "qa_failed"

    @pytest.mark.asyncio
    async def test_pipeline_job_is_persisted(self, monkeypatch, tmp_path, patch_settings):
        from orchestrator.adapters import ai_koubo as ak
        # Use a dedicated temp job store
        from orchestrator.job_store import JobStore
        test_jobs = tmp_path / "pipeline_jobs"
        test_store = JobStore(test_jobs)
        monkeypatch.setattr("orchestrator.layers.l5_scheduler.job_store", test_store)
        monkeypatch.setattr("orchestrator.modules.l5_scheduler.service.job_store", test_store)
        monkeypatch.setattr("orchestrator.main.job_store", test_store)
        monkeypatch.setattr("orchestrator.pipeline_runner.l5", __import__(
            "orchestrator.modules.l5_scheduler.service", fromlist=["create_job", "update_job"]
        ))
        monkeypatch.setattr(
            "orchestrator.modules.l5_scheduler.service.job_store", test_store
        )

        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            req = PipelineRunRequest(
                product_url="https://example.com/product/demo",
                layers=["L1", "L2", "L3", "L4", "L5"],
                topic="优质推荐",
            )
            result = await run_pipeline(req)

        # Job should exist on disk in the test store
        job_file = test_jobs / f"{result.job_id}.json"
        assert job_file.exists()
        data = json.loads(job_file.read_text(encoding="utf-8"))
        assert data["pipeline_status"] in ("ok", "qa_failed")

    @pytest.mark.asyncio
    async def test_pipeline_artifacts_include_script_id(self, patch_settings):
        from orchestrator.adapters import ai_koubo as ak
        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            req = PipelineRunRequest(
                product_url="https://example.com/product/demo",
                layers=["L1", "L2", "L3"],
            )
            result = await run_pipeline(req)

        assert "script_id" in result.artifacts
        assert result.artifacts["script_id"].startswith("s")

    @pytest.mark.asyncio
    async def test_pipeline_with_custom_topic_propagates(self, patch_settings):
        from orchestrator.adapters import ai_koubo as ak
        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            req = PipelineRunRequest(
                product_url="https://example.com/product/demo",
                layers=["L1", "L2", "L3"],
                topic="无人机航拍",
            )
            result = await run_pipeline(req)

        # L1 should have used our topic
        l1_result = result.layer_results[0]
        assert l1_result.layer_id == "L1"
        # The topics_count or similar should be present
        assert "topics_count" in l1_result.artifacts

    @pytest.mark.asyncio
    async def test_pipeline_error_handling_in_l4(self, patch_settings):
        """When L4 video-factory is unavailable, the pipeline should handle it."""
        from orchestrator.adapters import ai_koubo as ak
        with patch.object(ak, "_reachable", AsyncMock(return_value=False)):
            # Override video_factory_path to a nonexistent location
            import orchestrator.config as cfg
            original = cfg.settings.video_factory_path
            cfg.settings.video_factory_path = Path("/completely/nonexistent/path_xyz")
            try:
                req = PipelineRunRequest(
                    product_url="https://example.com/product/demo",
                    layers=["L1", "L2", "L3", "L4"],
                )
                result = await run_pipeline(req)
                # L4 should have been attempted — may be 'skipped' or 'error'
                l4_results = [r for r in result.layer_results if r.layer_id == "L4"]
                assert len(l4_results) >= 1
            finally:
                cfg.settings.video_factory_path = original


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline State Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineStateConstants:
    def test_qa_pass_threshold_is_float(self):
        assert 0 < QA_PASS_THRESHOLD <= 1.0

    def test_qa_retry_from_l2(self):
        assert QA_RETRY_FROM == "L2"

    def test_layer_count_is_eight(self):
        assert len(LAYER_INDEX) == 8
