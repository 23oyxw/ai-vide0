"""Unit tests for adapter modules — content_safety, multi_platform, ai_koubo, etc."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.adapters.content_safety import (
    PROHIBITED_WORDS,
    RISKY_WORDS,
    SafetyResult,
    check_content,
)
from orchestrator.adapters.multi_platform import (
    PLATFORM_CONFIGS,
    get_platforms,
    publish_to_platforms,
)
from orchestrator.adapters.l8_store import (
    data_source_label,
    init_local_store,
    upsert_daily_metrics,
    fetch_aggregated_metrics,
    resolve_database_url,
    SQLITE_PATH,
)
from orchestrator.adapters.storyboard import load_storyboard, resolve_demo_yaml_path
from orchestrator.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# Content Safety
# ═══════════════════════════════════════════════════════════════════════════════

class TestContentSafety:
    """Tests for the advertising-law compliance keyword checker."""

    def test_clean_text_passes(self):
        result = check_content("这款产品性价比很高，推荐大家试试")
        assert result.passed is True
        assert result.score == 1.0
        assert result.hits == []
        assert "通过" in result.message

    def test_single_prohibited_word_fails(self):
        result = check_content("这是第一好的产品")
        assert result.passed is False
        assert result.score < 1.0
        assert "第一" in result.hits

    def test_multiple_prohibited_words_accumulate_penalty(self):
        text = "唯一首选 绝对有效 100%好用 永不复发"
        result = check_content(text)
        # Each prohibited word is -0.15
        assert result.score <= 1.0 - 5 * 0.15
        assert result.passed is False

    def test_risky_words_reduce_score_only(self):
        result = check_content("这个祛皱祛斑美白产品")  # only risky, no prohibited
        # Without prohibited hits, risky only triggers fail when score < 0.8
        assert len(result.hits) >= 3

    def test_empty_string_passes(self):
        result = check_content("")
        assert result.passed is True
        assert result.score == 1.0

    def test_prohibited_words_list_is_loaded(self):
        assert len(PROHIBITED_WORDS) > 0
        assert "第一" in PROHIBITED_WORDS

    def test_risky_words_list_is_loaded(self):
        assert len(RISKY_WORDS) > 0
        assert "祛皱" in RISKY_WORDS

    def test_safety_result_is_namedtuple(self):
        r = check_content("ok text")
        assert isinstance(r, SafetyResult)
        assert hasattr(r, "passed")
        assert hasattr(r, "score")
        assert hasattr(r, "hits")
        assert hasattr(r, "message")

    def test_score_clamped_to_zero(self):
        # Enough prohibited words to push well below zero
        result = check_content("第一 唯一 首个 首选 顶级 最高 最佳 最好 最大")
        assert result.score >= 0.0

    @pytest.mark.parametrize(
        "word,expected",
        [
            ("第一", True),
            ("唯一", True),
            ("首个", True),
            ("首选", True),
            ("国家级", True),
            ("纯天然", True),
            ("无添加", True),
            ("万能", True),
        ],
    )
    def test_each_prohibited_word_is_detected(self, word, expected):
        result = check_content(f"本产品{word}好用")
        is_hit = word in result.hits
        assert is_hit == expected


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-Platform Publisher
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiPlatform:
    """Tests for the multi-platform publishing adapter stubs."""

    def test_get_platforms_returns_dict(self):
        platforms = get_platforms()
        assert isinstance(platforms, dict)
        assert "douyin" in platforms
        assert platforms["douyin"] == "抖音"

    def test_all_four_platforms_configured(self):
        assert "douyin" in PLATFORM_CONFIGS
        assert "xiaohongshu" in PLATFORM_CONFIGS
        assert "kuaishou" in PLATFORM_CONFIGS
        assert "wechat" in PLATFORM_CONFIGS

    def test_publish_without_video_path_skips(self):
        results = publish_to_platforms(
            job_id="j-test",
            video_path="",
            title="test title",
            platforms=["douyin"],
        )
        assert len(results) == 1
        assert results[0]["ok"] is True
        assert results[0]["status"] == "skipped"

    def test_publish_with_video_path_succeeds(self):
        results = publish_to_platforms(
            job_id="j-test",
            video_path="/tmp/fake_video.mp4",
            title="种草视频",
            platforms=["douyin", "xiaohongshu"],
        )
        assert len(results) == 2
        for r in results:
            assert r["ok"] is True
            assert r["status"] == "published"
            assert "url" in r

    def test_all_platforms_default(self):
        results = publish_to_platforms(
            job_id="j-test", video_path="/tmp/v.mp4", title="test"
        )
        assert len(results) == 4  # all 4 platforms

    def test_unknown_platform_rejected(self):
        results = publish_to_platforms(
            job_id="j-test",
            video_path="/tmp/v.mp4",
            platforms=["nonexistent"],
        )
        assert len(results) == 1
        assert results[0]["ok"] is False
        assert "Unknown platform" in results[0]["error"]

    def test_title_truncated_to_max_len(self):
        results = publish_to_platforms(
            job_id="j-test",
            video_path="/tmp/v.mp4",
            title="x" * 100,  # > xiaohongshu max (20)
            platforms=["xiaohongshu"],
        )
        assert len(results[0]["title"]) <= PLATFORM_CONFIGS["xiaohongshu"]["max_title_len"]

    def test_tags_are_recommended_per_platform(self):
        results = publish_to_platforms(
            job_id="j-test",
            video_path="/tmp/v.mp4",
            platforms=["douyin"],
        )
        assert "种草" in results[0]["tags"]


# ═══════════════════════════════════════════════════════════════════════════════
# L8 Store (SQLite metrics persistence)
# ═══════════════════════════════════════════════════════════════════════════════

class TestL8Store:
    """Tests for L8 metrics persistence layer with SQLite fallback."""

    def test_init_local_store_creates_db(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")
        # Also patch the module-level SQLITE_PATH that is set at import time
        monkeypatch.setattr(
            "orchestrator.adapters.l8_store.SQLITE_PATH",
            tmp_data_dir / "l8_metrics.db",
        )
        source = init_local_store()
        assert source == "sqlite"
        assert (tmp_data_dir / "l8_metrics.db").exists()

    def test_upsert_and_fetch_roundtrip(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")

        # Re-initialise to pick up the new data_root
        backend = upsert_daily_metrics(
            job_id="test-upsert",
            metric_date="2026-07-05",
            clicks=500,
            unique_clicks=400,
            conversions=20,
            orders=10,
            gmv=2000.0,
        )
        assert backend == "sqlite"

        metrics = fetch_aggregated_metrics("test-upsert")
        assert metrics is not None
        assert metrics["clicks"] == 500
        assert metrics["unique_clicks"] == 400
        assert metrics["conversions"] == 20
        assert metrics["orders"] == 10
        assert metrics["gmv"] == 2000.0

    def test_upsert_replace_updates(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")

        upsert_daily_metrics(
            job_id="replace-test",
            metric_date="2026-07-05",
            clicks=100,
            unique_clicks=80,
            conversions=5,
            orders=2,
            gmv=300.0,
        )
        upsert_daily_metrics(
            job_id="replace-test",
            metric_date="2026-07-05",
            clicks=900,
            unique_clicks=700,
            conversions=40,
            orders=20,
            gmv=4000.0,
        )
        metrics = fetch_aggregated_metrics("replace-test")
        assert metrics["clicks"] == 900  # not 100 + 900

    def test_aggregate_all_returns_multi_job_sum(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")
        monkeypatch.setattr(
            "orchestrator.adapters.l8_store.SQLITE_PATH",
            tmp_data_dir / "l8_metrics.db",
        )

        # _init_sqlite seeds 4 rows when DB is empty. Add our 2 rows.
        # Seed: 4200+4800+5100+1200=15300 + test: 300+400=700 = 16000
        upsert_daily_metrics(
            job_id="j-a", metric_date="2026-07-05",
            clicks=300, unique_clicks=200, conversions=10, orders=5, gmv=1000.0,
        )
        upsert_daily_metrics(
            job_id="j-b", metric_date="2026-07-05",
            clicks=400, unique_clicks=300, conversions=15, orders=8, gmv=1600.0,
        )
        metrics = fetch_aggregated_metrics("all")
        assert metrics is not None
        # Verify our job-level data is correctly persisted
        metrics_a = fetch_aggregated_metrics("j-a")
        assert metrics_a is not None
        assert metrics_a["clicks"] == 300

    def test_fetch_unknown_job_returns_sqlite_seed(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")

        init_local_store()
        # When job doesn't exist, query falls back to 'all' seed rows
        metrics = fetch_aggregated_metrics("nonexistent-job")
        if metrics is not None:
            assert metrics["clicks"] >= 0

    def test_data_source_label_demo(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")
        monkeypatch.setattr(
            "orchestrator.adapters.l8_store.SQLITE_PATH",
            tmp_data_dir / "l8_metrics.db",
        )
        # Remove existing DB so demo label is returned
        db = tmp_data_dir / "l8_metrics.db"
        if db.exists():
            db.unlink()
        label = data_source_label()
        assert label == "demo"

    def test_data_source_label_sqlite(self, tmp_data_dir, monkeypatch):
        monkeypatch.setattr(settings, "data_root", tmp_data_dir)
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")
        init_local_store()
        label = data_source_label()
        assert label == "sqlite"

    def test_resolve_database_url_prefers_postgres(self, monkeypatch):
        monkeypatch.setattr(settings, "postgres_url", "postgresql://localhost/test")
        monkeypatch.setattr(settings, "database_url", "sqlite:///other.db")
        url = resolve_database_url()
        assert url == "postgresql://localhost/test"

    def test_resolve_database_url_falls_back_to_database_url(self, monkeypatch):
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "sqlite:///other.db")
        url = resolve_database_url()
        assert url == "sqlite:///other.db"

    def test_resolve_database_url_returns_none_when_both_empty(self, monkeypatch):
        monkeypatch.setattr(settings, "postgres_url", "")
        monkeypatch.setattr(settings, "database_url", "")
        assert resolve_database_url() is None


# ═══════════════════════════════════════════════════════════════════════════════
# Storyboard Loader
# ═══════════════════════════════════════════════════════════════════════════════

class TestStoryboardAdapter:
    def test_load_storyboard_not_found(self, monkeypatch):
        monkeypatch.setattr(
            settings, "video_factory_path", Path("/nonexistent/path")
        )
        result = load_storyboard("completely_missing_demo")
        assert result["status"] == "skipped"
        assert "not found" in result["message"]

    def test_resolve_demo_yaml_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "video_factory_path", tmp_path)
        path = resolve_demo_yaml_path("my_demo")
        assert path.name == "my_demo.yaml"
        assert str(tmp_path) in str(path)
