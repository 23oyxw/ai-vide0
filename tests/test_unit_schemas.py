"""Unit tests for Pydantic schemas — validation, defaults, serialisation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from orchestrator.schemas import (
    ApiEnvelope,
    ApiError,
    ApiMeta,
    CrawlerData,
    CrawlerRequest,
    DataAnalysisData,
    DataAnalysisRequest,
    DataClickData,
    DataClickQuery,
    DataConversionData,
    DataConversionQuery,
    DataOrderData,
    DataOrderQuery,
    HealthData,
    LayerResultPayload,
    MonitorCheck,
    MonitorData,
    MonitorRequest,
    PipelineRunData,
    PipelineRunRequest,
    SelectionCard,
    ToolsCheckData,
    err_envelope,
    ok_envelope,
)
from orchestrator.pipeline_state import LAYER_INDEX, LAYER_ORDER, PipelineState


# ── PipelineRunRequest ─────────────────────────────────────────────────────────

class TestPipelineRunRequest:
    def test_defaults_produce_valid_request(self):
        req = PipelineRunRequest()
        assert req.demo_name == "post_production_15s_zhongcao"
        assert req.layers == ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
        assert req.force_qa_fail is False

    def test_custom_layers_accepted(self):
        req = PipelineRunRequest(layers=["L1", "L2", "L3"])
        assert req.layers == ["L1", "L2", "L3"]

    def test_none_product_url_allowed(self):
        req = PipelineRunRequest(product_url=None)
        assert req.product_url is None

    def test_topic_and_script_optional(self):
        req = PipelineRunRequest(topic="防晒", script="今天...")
        assert req.topic == "防晒"
        assert req.script == "今天..."

    def test_force_qa_fail_flag(self):
        req = PipelineRunRequest(force_qa_fail=True)
        assert req.force_qa_fail is True


# ── ApiEnvelope / ok_envelope / err_envelope ──────────────────────────────────

class TestApiEnvelope:
    def test_ok_envelope_wraps_data(self):
        env = ok_envelope(HealthData(status="ok", version="0.1", layers=["L1"]), layer="L0")
        assert env.ok is True
        assert env.data.status == "ok"
        assert env.meta.layer == "L0"
        assert env.error is None
        assert env.meta.timestamp

    def test_err_envelope_has_error(self):
        env = err_envelope(code="test_404", message="Not found", layer="L5")
        assert env.ok is False
        assert env.data is None
        assert env.error.code == "test_404"
        assert env.error.message == "Not found"
        assert env.meta.layer == "L5"

    def test_err_envelope_with_detail(self):
        env = err_envelope("val_err", "bad input", detail={"field": "x"}, job_id="j1")
        assert env.error.detail == {"field": "x"}
        assert env.meta.job_id == "j1"

    def test_ok_envelope_serializes(self):
        env = ok_envelope({"key": "value"})
        d = env.model_dump()
        assert d["ok"] is True
        assert d["data"] == {"key": "value"}


# ── LayerResultPayload ─────────────────────────────────────────────────────────

class TestLayerResultPayload:
    def test_full_result(self):
        r = LayerResultPayload(
            layer_id="L2",
            status="ok",
            message="script generated",
            artifacts={"script": "demo text"},
        )
        assert r.status == "ok"
        assert r.artifacts["script"] == "demo text"

    def test_empty_artifacts(self):
        r = LayerResultPayload(layer_id="L1", status="error", message="timeout")
        assert r.artifacts == {}


# ── PipelineRunData ────────────────────────────────────────────────────────────

class TestPipelineRunData:
    def test_full_response_roundtrips(self):
        data = PipelineRunData(
            job_id="j-test-001",
            status="ok",
            pipeline_state="published",
            layers=["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
            layer_results=[
                LayerResultPayload(layer_id="L1", status="ok", artifacts={"crawled_url": "http://x"})
            ],
            artifacts={"video_path": "/tmp/out.mp4"},
            errors=[],
            optimization_hints=["L2: improve hook"],
        )
        d = data.model_dump()
        assert d["job_id"] == "j-test-001"
        assert d["pipeline_state"] == "published"
        assert len(d["layer_results"]) == 1
        assert d["optimization_hints"] == ["L2: improve hook"]

    def test_retry_from_field(self):
        data = PipelineRunData(
            job_id="j1",
            status="qa_failed",
            pipeline_state="qa_failed",
            layers=["L1", "L2", "L3", "L4", "L5", "L6"],
            layer_results=[],
            artifacts={},
            errors=["QA score 0.6 below threshold"],
            retry_from="L2",
        )
        assert data.retry_from == "L2"


# ── Health / Tools schemas ────────────────────────────────────────────────────

class TestHealthToolsSchemas:
    def test_health_data(self):
        h = HealthData(status="ok", version="1.0", layers=["L1", "L2"])
        assert h.status == "ok"
        assert h.version == "1.0"

    def test_tools_check_data(self):
        t = ToolsCheckData(
            video_factory={"path": "/tmp", "exists": True, "demos": []},
            ai_koubo={"path": "/tmp", "exists": False, "url": "http://x"},
            c4d={"commandline": "/tmp/c4d.exe"},
            ffmpeg={"path": "/tmp/ffmpeg", "exists": True},
            openclaw={"bin": "openclaw"},
        )
        assert t.video_factory["exists"] is True
        assert t.ai_koubo["exists"] is False


# ── L1 Crawler schemas ────────────────────────────────────────────────────────

class TestCrawlerSchemas:
    def test_selection_card(self):
        card = SelectionCard(title="防晒好物", pain_points=["不知道选哪个", "怕油腻"], category="护肤")
        assert len(card.pain_points) == 2

    def test_crawler_request(self):
        req = CrawlerRequest(
            product_url="https://example.com/p/1",
            competitor_urls=["https://example.com/c/1", "https://example.com/c/2"],
        )
        assert len(req.competitor_urls) == 2

    def test_crawler_data(self):
        data = CrawlerData(
            crawled_url="https://example.com/p/1",
            selection_card=SelectionCard(title="x"),
            competitor_count=3,
        )
        assert data.competitor_count == 3


# ── L6 Monitor schemas ────────────────────────────────────────────────────────

class TestMonitorSchemas:
    def test_monitor_check(self):
        ch = MonitorCheck(name="duration_15s", passed=True, score=1.0, message="ok")
        assert ch.passed is True

    def test_monitor_data(self):
        md = MonitorData(
            qa_score_avg=0.85,
            active_jobs=3,
            checks=[MonitorCheck(name="final_video_exists", passed=True)],
            message="all ok",
        )
        assert md.qa_score_avg == 0.85
        assert md.active_jobs == 3


# ── L8 Data schemas ───────────────────────────────────────────────────────────

class TestDataSchemas:
    def test_click_query_defaults(self):
        q = DataClickQuery()
        assert q.job_id is None
        assert q.utm_campaign is None

    def test_click_data(self):
        d = DataClickData(clicks=1000, unique_clicks=750, ctr=0.04, records=[])
        assert d.clicks == 1000

    def test_conversion_data(self):
        d = DataConversionData(conversions=50, conversion_rate=0.067, records=[])
        assert d.conversions == 50

    def test_order_data(self):
        d = DataOrderData(orders=30, gmv=5970.0, records=[])
        assert d.orders == 30
        assert d.gmv == 5970.0

    def test_analysis_data(self):
        d = DataAnalysisData(
            summary="CTR 4%",
            optimization_hints=["L2: improve hook"],
            feedback_targets=["L1", "L2"],
        )
        assert len(d.optimization_hints) == 1


# ── PipelineState enum ─────────────────────────────────────────────────────────

class TestPipelineState:
    def test_all_states_defined(self):
        states = {s.value for s in PipelineState}
        assert "pending" in states
        assert "running" in states
        assert "qa_failed" in states
        assert "published" in states
        assert "analyzed" in states
        assert "error" in states

    def test_string_coercion(self):
        assert PipelineState("running") == PipelineState.RUNNING


# ── Layer ordering ─────────────────────────────────────────────────────────────

class TestLayerOrder:
    def test_order_is_eight_layers(self):
        assert len(LAYER_ORDER) == 8

    def test_all_layer_ids_present(self):
        assert "L1" in LAYER_ORDER
        assert "L8" in LAYER_ORDER

    def test_index_monotonic(self):
        for i, lid in enumerate(LAYER_ORDER):
            assert LAYER_INDEX[lid] == i

    def test_validate_order_success(self):
        from orchestrator.main import validate_layer_order
        validate_layer_order(["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"])

    def test_validate_order_rejects_reverse(self):
        from orchestrator.main import validate_layer_order
        from fastapi import HTTPException
        with pytest.raises(HTTPException, match="Layer order violation"):
            validate_layer_order(["L3", "L1"])

    def test_validate_order_rejects_duplicate(self):
        from orchestrator.main import validate_layer_order
        from fastapi import HTTPException
        with pytest.raises(HTTPException, match="Layer order violation"):
            validate_layer_order(["L1", "L1"])

    def test_validate_order_rejects_unknown(self):
        from orchestrator.main import validate_layer_order
        from fastapi import HTTPException
        with pytest.raises(HTTPException, match="Unknown layer"):
            validate_layer_order(["L99"])
