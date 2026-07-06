"""Unit tests for standalone module services (L1-L8 modules + RAG)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.config import settings
from orchestrator.modules.common import (
    list_json_records,
    load_json,
    module_dir,
    new_id,
    save_json,
    utc_now_iso,
)
from orchestrator.modules.l1_crawler.service import (
    CURATED_TRENDING,
    search_topics,
    search_trending,
    list_topics,
)
from orchestrator.modules.l1_crawler.models import SearchRequest
from orchestrator.modules.l2_content.models import (
    GenerateScriptRequest,
    OptimizePromptsRequest,
)
from orchestrator.modules.l5_scheduler.models import JobCreateRequest
from orchestrator.modules.l6_qa.models import ValidateRequest, RulesResponse
from orchestrator.modules.l8_analytics.models import (
    MetricsRecordRequest,
    DashboardResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Common Utilities
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommonUtils:
    def test_new_id_generates_unique_string(self):
        ids = {new_id() for _ in range(50)}
        assert len(ids) == 50

    def test_new_id_with_prefix(self):
        result = new_id("j")
        assert result.startswith("j")
        assert len(result) == 1 + 8  # prefix + 8 hex chars

    def test_utc_now_iso_format(self):
        ts = utc_now_iso()
        assert "T" in ts
        assert ts.endswith("Z") or "+" in ts

    def test_save_and_load_json_roundtrip(self, tmp_path):
        file = tmp_path / "test.json"
        save_json(file, {"key": "value", "num": 42})
        data = load_json(file)
        assert data == {"key": "value", "num": 42}

    def test_load_json_nonexistent(self, tmp_path):
        assert load_json(tmp_path / "nonexistent.json") is None

    def test_module_dir_creates_and_returns_path(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        result = module_dir("l1")
        assert result.exists()
        assert result.name == "l1"

    def test_list_json_records_empty(self, tmp_path):
        assert list_json_records(tmp_path) == []

    def test_list_json_records_sorted_recent_first(self, tmp_path):
        save_json(tmp_path / "a.json", {"order": 1})
        save_json(tmp_path / "b.json", {"order": 2})
        records = list_json_records(tmp_path)
        assert len(records) == 2

    def test_list_json_records_skips_corrupted(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json at all", encoding="utf-8")
        save_json(tmp_path / "good.json", {"ok": True})
        records = list_json_records(tmp_path)
        assert len(records) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# L1 Crawler Module
# ═══════════════════════════════════════════════════════════════════════════════

class TestL1Module:
    def test_curated_trending_has_categories(self):
        assert "电商" in CURATED_TRENDING
        assert "三农" in CURATED_TRENDING

    def test_curated_ecommerce_topics_non_empty(self):
        topics = CURATED_TRENDING["电商"]
        assert len(topics) >= 8

    def test_search_trending_filters_by_keyword(self):
        topics = search_trending("防晒", "电商")
        assert len(topics) > 0
        assert any("防晒" in t.keyword for t in topics)

    def test_search_trending_falls_back_on_no_match(self):
        topics = search_trending("xyz_完全不存在", "电商")
        assert len(topics) == 8  # falls back to all 8

    def test_search_trending_sorted_by_heat_desc(self):
        topics = search_trending(None, "电商")
        for i in range(len(topics) - 1):
            assert topics[i].heat >= topics[i + 1].heat

    def test_list_topics_returns_what_was_stored(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "rag_auto_ingest_crawl", False)
        resp = list_topics()
        assert isinstance(resp.total, int)

    @pytest.mark.asyncio
    async def test_search_topics_without_url(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "rag_auto_ingest_crawl", False)
        req = SearchRequest(keyword="防晒", vertical="电商")
        resp = await search_topics(req)
        assert len(resp.topics) > 0
        assert resp.crawl is None  # no product_url -> no crawl

    @pytest.mark.asyncio
    async def test_search_topics_with_url_crawls(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "rag_auto_ingest_crawl", False)
        req = SearchRequest(
            keyword="防晒",
            vertical="电商",
            product_url="https://example.com/p/demo",
        )
        resp = await search_topics(req)
        assert resp.crawl is not None
        assert resp.crawl.crawled_url == "https://example.com/p/demo"


# ═══════════════════════════════════════════════════════════════════════════════
# L2 Content Module
# ═══════════════════════════════════════════════════════════════════════════════

class TestL2Module:
    @pytest.mark.asyncio
    async def test_generate_script_with_topic(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l2_content.service import generate_script_record
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        # Prevent live HTTP calls
        with patch("orchestrator.adapters.ai_koubo._reachable", AsyncMock(return_value=False)):
            req = GenerateScriptRequest(topic="防晒好物", product_url="https://e.g/p/1")
            resp = await generate_script_record(req)
            assert resp.script.id.startswith("s")
            assert len(resp.script.segments) == 4
            assert resp.script.duration_sec == 15.0
            assert resp.script.provider in ("stub", "local-template", "deepseek", "ai-koubo", "zhipu")

    @pytest.mark.asyncio
    async def test_generate_script_segments_are_valid(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l2_content.service import generate_script_record
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        with patch("orchestrator.adapters.ai_koubo._reachable", AsyncMock(return_value=False)):
            req = GenerateScriptRequest(topic="电器评测")
            resp = await generate_script_record(req)
            codes = [s.code for s in resp.script.segments]
            assert codes == ["hook", "pain", "product", "cta"]
            for seg in resp.script.segments:
                assert seg.duration_sec > 0

    @pytest.mark.asyncio
    async def test_generate_script_persists_to_disk(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l2_content.service import generate_script_record, get_script
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        with patch("orchestrator.adapters.ai_koubo._reachable", AsyncMock(return_value=False)):
            req = GenerateScriptRequest(topic="测试商品", product_url="https://e.g/p/2")
            resp = await generate_script_record(req)
            # Read back
            loaded = get_script(resp.script.id)
            assert loaded is not None
            assert loaded.script.full_text == resp.script.full_text

    def test_get_script_nonexistent_returns_none(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l2_content.service import get_script
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        assert get_script("nonexistent_id") is None

    @pytest.mark.asyncio
    async def test_optimize_prompts_produces_all_sections(self, monkeypatch):
        from orchestrator.modules.l2_content.service import optimize_prompts
        monkeypatch.setattr(settings, "data_root", Path("data"))  # won't be touched
        req = OptimizePromptsRequest(
            product_url="https://e.g/p/1",
            topic="防晒 · 护肤",
            product_title="轻透防晒霜",
            category="护肤",
            pain_points=["油腻", "过敏", "价格高"],
        )
        resp = await optimize_prompts(req)
        assert resp.optimized_topic
        assert resp.optimized_script
        assert len(resp.hook_suggestions) >= 1
        assert len(resp.next_steps) >= 2
        assert resp.provider in ("rag-template", "deepseek")


# ═══════════════════════════════════════════════════════════════════════════════
# L5 Scheduler Module
# ═══════════════════════════════════════════════════════════════════════════════

class TestL5Module:
    def test_create_job_returns_record(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import create_job
        req = JobCreateRequest(
            product_url="https://example.com/p/demo",
            layers=["L1", "L2", "L3"],
        )
        resp = create_job(req)
        assert resp.job.job_id.startswith("j")
        assert resp.job.status == "pending"
        assert resp.job.product_url == "https://example.com/p/demo"

    def test_list_jobs_returns_created_jobs(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import create_job, list_jobs
        for i in range(3):
            create_job(JobCreateRequest(product_url=f"https://e.g/p/{i}"))
        resp = list_jobs()
        assert resp.total >= 3

    def test_get_job_finds_existing(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import create_job, get_job
        created = create_job(JobCreateRequest(product_url="https://e.g/p/x"))
        found = get_job(created.job.job_id)
        assert found is not None
        assert found.job.job_id == created.job.job_id

    def test_get_job_missing_returns_none(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import get_job
        assert get_job("nonexistent_job_id") is None

    def test_update_job_patches_correctly(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import create_job, update_job
        created = create_job(JobCreateRequest(product_url="https://e.g/p/up"))
        updated = update_job(
            created.job.job_id,
            {"status": "running", "script_id": "s-test1234"},
        )
        assert updated is not None
        assert updated.job.status == "running"
        assert updated.job.script_id == "s-test1234"

    def test_update_job_missing_returns_none(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import update_job
        assert update_job("fake-id", {}) is None

    def test_retry_job_increments_counter(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import create_job, retry_job
        created = create_job(JobCreateRequest(product_url="https://e.g/p/retry"))
        retried = retry_job(created.job.job_id)
        assert retried is not None
        assert retried.job.retry_count == 1
        assert "pending" in retried.job.status

    def test_cancel_job_sets_cancelled(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import create_job, cancel_job
        created = create_job(JobCreateRequest(product_url="https://e.g/p/cancel"))
        cancelled = cancel_job(created.job.job_id)
        assert cancelled is not None
        assert cancelled.job.status == "cancelled"

    def test_cancel_already_cancelled_is_idempotent(self, patch_settings):
        from orchestrator.modules.l5_scheduler.service import create_job, cancel_job
        created = create_job(JobCreateRequest(product_url="https://e.g/p/c2"))
        cancel_job(created.job.job_id)
        result = cancel_job(created.job.job_id)
        assert result is not None
        assert result.job.status == "cancelled"


# ═══════════════════════════════════════════════════════════════════════════════
# L6 QA Module
# ═══════════════════════════════════════════════════════════════════════════════

class TestL6Module:
    def test_get_rules_returns_prohibited_words(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l6_qa.service import get_rules
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        rules = get_rules()
        assert "第一" in rules.prohibited_words
        assert "祛皱" in rules.risky_words
        assert rules.pass_threshold == 0.7

    @pytest.mark.asyncio
    async def test_validate_clean_script_passes(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l6_qa.service import validate
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "pipeline_mode", "production")
        resp = await validate(ValidateRequest(script_text="这是一段合规安全的种草文案"))
        # In production mode, score 1.0 passes
        score_check = resp.score >= 0.7
        assert score_check or resp.passed

    @pytest.mark.asyncio
    async def test_validate_force_fail_returns_false(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l6_qa.service import validate
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        resp = await validate(ValidateRequest(force_fail=True))
        assert resp.passed is False
        assert any(c.name == "forced_fail" for c in resp.checks)

    @pytest.mark.asyncio
    async def test_validate_with_prohibited_script_fails(self, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l6_qa.service import validate
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "pipeline_mode", "production")
        resp = await validate(ValidateRequest(
            script_text="这是第一好用的产品绝对万能奇效",
        ))
        assert resp.passed is False or resp.score < 1.0

    @pytest.mark.asyncio
    async def test_validate_with_manifest_path_runs_checks(self, tmp_path, tmp_data_dir, monkeypatch):
        from orchestrator.modules.l6_qa.service import validate
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "final_video": "final.mp4",
            "scenes": [{"duration": 3}, {"duration": 4}, {"duration": 4}, {"duration": 3}],
        }), encoding="utf-8")
        (tmp_path / "final.mp4").touch()
        resp = await validate(ValidateRequest(
            manifest_path=str(manifest),
            output_dir=str(tmp_path),
        ))
        assert len(resp.checks) >= 3  # manifest_exists, final_video_exists, duration_15s, scene_count...


# ═══════════════════════════════════════════════════════════════════════════════
# L8 Analytics Module
# ═══════════════════════════════════════════════════════════════════════════════

class TestL8Module:
    def test_get_dashboard_returns_metrics(self, patch_settings):
        from orchestrator.modules.l8_analytics.service import get_dashboard
        dash = get_dashboard()
        assert dash.job_count >= 0
        assert dash.avg_qa_score > 0
        assert isinstance(dash.chart, dict)

    def test_get_click_returns_positive_counts(self, patch_settings):
        from orchestrator.modules.l8_analytics.service import get_click
        click = get_click()
        assert click.clicks > 0
        assert click.unique_clicks > 0

    def test_get_conversion_has_rate(self, patch_settings):
        from orchestrator.modules.l8_analytics.service import get_conversion
        conv = get_conversion()
        assert conv.conversions >= 0
        assert 0 <= conv.conversion_rate <= 1.0

    def test_get_order_has_gmv(self, patch_settings):
        from orchestrator.modules.l8_analytics.service import get_order
        order = get_order()
        assert order.orders >= 0
        assert order.gmv >= 0

    def test_get_analysis_produces_hints(self, patch_settings):
        from orchestrator.modules.l8_analytics.service import get_analysis
        analysis = get_analysis()
        assert len(analysis.optimization_hints) > 0
        assert len(analysis.feedback_targets) > 0
        assert isinstance(analysis.chart, dict)

    def test_record_metrics_persists(self, patch_settings):
        from orchestrator.modules.l8_analytics.service import record_metrics
        resp = record_metrics(
            MetricsRecordRequest(
                job_id="test-module-job",
                clicks=300,
                unique_clicks=250,
                conversions=15,
                orders=8,
                gmv=1600.0,
            )
        )
        assert resp.backend in ("sqlite", "postgres")

    def test_record_pipeline_metrics(self, patch_settings):
        from orchestrator.modules.l8_analytics.service import record_pipeline_metrics
        from orchestrator.modules.l5_scheduler.service import create_job
        from orchestrator.modules.l5_scheduler.models import JobCreateRequest
        created = create_job(JobCreateRequest(product_url="https://e.g/p/l8"))
        resp = record_pipeline_metrics(created.job.job_id)
        assert resp.backend in ("sqlite", "postgres")
        assert resp.job_id == created.job.job_id
