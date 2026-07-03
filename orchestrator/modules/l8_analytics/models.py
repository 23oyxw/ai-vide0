from __future__ import annotations

from pydantic import BaseModel, Field


class MetricSeriesPoint(BaseModel):
    date: str
    value: float


class EChartsSeries(BaseModel):
    name: str
    type: str = "line"
    data: list[float]


class DashboardResponse(BaseModel):
    job_count: int
    published_count: int
    avg_qa_score: float
    total_clicks: int
    total_conversions: int
    total_orders: int
    total_gmv: float
    chart: dict[str, object] = Field(default_factory=dict)


class ClickResponse(BaseModel):
    clicks: int
    unique_clicks: int
    ctr: float
    records: list[dict[str, object]] = Field(default_factory=list)
    chart: dict[str, object] = Field(default_factory=dict)


class ConversionResponse(BaseModel):
    conversions: int
    conversion_rate: float
    records: list[dict[str, object]] = Field(default_factory=list)
    chart: dict[str, object] = Field(default_factory=dict)


class OrderResponse(BaseModel):
    orders: int
    gmv: float
    records: list[dict[str, object]] = Field(default_factory=list)
    chart: dict[str, object] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    summary: str
    optimization_hints: list[str] = Field(default_factory=list)
    feedback_targets: list[str] = Field(default_factory=list)
    chart: dict[str, object] = Field(default_factory=dict)
