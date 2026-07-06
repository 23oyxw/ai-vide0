from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from orchestrator.layers import DEFAULT_PIPELINE

T = TypeVar("T")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ApiMeta(BaseModel):
    layer: str | None = None
    job_id: str | None = None
    timestamp: str = Field(default_factory=utc_now_iso)


class ApiError(BaseModel):
    code: str
    message: str
    detail: Any | None = None


class ApiEnvelope(BaseModel, Generic[T]):
    ok: bool
    data: T | None = None
    error: ApiError | None = None
    meta: ApiMeta = Field(default_factory=ApiMeta)


def ok_envelope(
    data: T,
    *,
    layer: str | None = None,
    job_id: str | None = None,
) -> ApiEnvelope[T]:
    return ApiEnvelope(
        ok=True,
        data=data,
        error=None,
        meta=ApiMeta(layer=layer, job_id=job_id, timestamp=utc_now_iso()),
    )


def err_envelope(
    code: str,
    message: str,
    *,
    layer: str | None = None,
    job_id: str | None = None,
    detail: Any | None = None,
) -> ApiEnvelope[None]:
    return ApiEnvelope(
        ok=False,
        data=None,
        error=ApiError(code=code, message=message, detail=detail),
        meta=ApiMeta(layer=layer, job_id=job_id, timestamp=utc_now_iso()),
    )


# ── L5 Pipeline ──────────────────────────────────────────────────────────────


class PipelineRunRequest(BaseModel):
    product_url: str | None = None
    demo_name: str = "post_production_15s_zhongcao"
    video_style: str = "real"  # real | product | 3d | unbox | compare
    c4d_project: str | None = None
    layers: list[str] = Field(default_factory=lambda: list(DEFAULT_PIPELINE))
    force_qa_fail: bool = False
    topic: str | None = None
    script: str | None = None


class LayerResultPayload(BaseModel):
    layer_id: str
    status: str
    message: str = ""
    artifacts: dict[str, str] = Field(default_factory=dict)


class PipelineRunData(BaseModel):
    job_id: str
    status: str
    pipeline_state: str
    layers: list[str]
    layer_results: list[LayerResultPayload]
    artifacts: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    retry_from: str | None = None
    optimization_hints: list[str] = Field(default_factory=list)


# ── L1 Crawler ───────────────────────────────────────────────────────────────


class CrawlerRequest(BaseModel):
    product_url: str | None = None
    competitor_urls: list[str] = Field(default_factory=list)
    job_id: str | None = None


class SelectionCard(BaseModel):
    title: str
    pain_points: list[str] = Field(default_factory=list)
    category: str = "general"


class CrawlerData(BaseModel):
    crawled_url: str
    selection_card: SelectionCard
    competitor_count: int = 0
    rag_candidates: list[str] = Field(default_factory=list)


# ── L6 Monitor ───────────────────────────────────────────────────────────────


class MonitorRequest(BaseModel):
    job_id: str | None = None
    video_url: str | None = None
    script_text: str | None = None


class MonitorCheck(BaseModel):
    name: str
    passed: bool
    score: float | None = None
    message: str = ""


class MonitorData(BaseModel):
    qa_score_avg: float
    active_jobs: int
    checks: list[MonitorCheck] = Field(default_factory=list)
    message: str = ""


# ── L8 Data ──────────────────────────────────────────────────────────────────


class DataClickQuery(BaseModel):
    job_id: str | None = None
    utm_campaign: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class DataClickData(BaseModel):
    clicks: int
    unique_clicks: int
    ctr: float
    records: list[dict[str, Any]] = Field(default_factory=list)


class DataConversionQuery(BaseModel):
    job_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class DataConversionData(BaseModel):
    conversions: int
    conversion_rate: float
    records: list[dict[str, Any]] = Field(default_factory=list)


class DataOrderQuery(BaseModel):
    job_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class DataOrderData(BaseModel):
    orders: int
    gmv: float
    records: list[dict[str, Any]] = Field(default_factory=list)


class DataAnalysisRequest(BaseModel):
    job_id: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class DataAnalysisData(BaseModel):
    summary: str
    optimization_hints: list[str] = Field(default_factory=list)
    feedback_targets: list[str] = Field(default_factory=list)


# ── Health / Tools ───────────────────────────────────────────────────────────


class HealthData(BaseModel):
    status: str
    version: str
    layers: list[str]


class ToolsCheckData(BaseModel):
    video_factory: dict[str, Any]
    ai_koubo: dict[str, Any]
    c4d: dict[str, Any]
    ffmpeg: dict[str, Any]
    openclaw: dict[str, Any]
