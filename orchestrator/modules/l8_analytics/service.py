from __future__ import annotations

import hashlib

from orchestrator.job_store import job_store
from orchestrator.modules.common import list_json_records, module_dir
from orchestrator.modules.l8_analytics.models import (
    AnalysisResponse,
    ClickResponse,
    ConversionResponse,
    DashboardResponse,
    OrderResponse,
)
from orchestrator.pipeline_state import QA_PASS_THRESHOLD

PUBLISHED_DIR = module_dir("l7", "published")


def _seed(job_id: str | None, salt: str) -> int:
    key = f"{job_id or 'all'}:{salt}"
    digest = hashlib.md5(key.encode()).hexdigest()
    return int(digest[:8], 16)


def _echarts_line(title: str, labels: list[str], series: list[dict]) -> dict:
    return {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": [s["name"] for s in series]},
        "xAxis": {"type": "category", "data": labels},
        "yAxis": {"type": "value"},
        "series": series,
    }


def _job_metrics(job_id: str | None) -> dict[str, float]:
    base = _seed(job_id, "metrics")
    clicks = 800 + (base % 5000)
    unique = int(clicks * 0.75)
    conversions = int(unique * (0.06 + (base % 30) / 1000))
    orders = int(conversions * 0.55)
    gmv = round(orders * (199 + (base % 400)), 2)
    ctr = round(clicks / max(unique * 25, 1), 4)
    cvr = round(conversions / max(unique, 1), 4)
    return {
        "clicks": clicks,
        "unique_clicks": unique,
        "ctr": ctr,
        "conversions": conversions,
        "conversion_rate": cvr,
        "orders": orders,
        "gmv": gmv,
    }


def _aggregate_jobs() -> tuple[int, float]:
    ids = job_store.list_jobs()
    scores: list[float] = []
    for jid in ids:
        raw = job_store.load(jid)
        if not raw:
            continue
        try:
            scores.append(float(raw.get("qa_score", 0) or 0))
        except ValueError:
            continue
    avg = sum(scores) / len(scores) if scores else 0.85
    return len(ids), avg


def get_dashboard(job_id: str | None = None) -> DashboardResponse:
    job_count, avg_qa = _aggregate_jobs()
    published_count = len(list_json_records(PUBLISHED_DIR))
    m = _job_metrics(job_id)
    labels = ["D-6", "D-5", "D-4", "D-3", "D-2", "D-1", "Today"]
    chart = _echarts_line(
        "运营概览",
        labels,
        [
            {"name": "点击", "type": "line", "data": [m["clicks"] * (0.7 + i * 0.05) for i in range(7)]},
            {"name": "转化", "type": "line", "data": [m["conversions"] * (0.6 + i * 0.06) for i in range(7)]},
        ],
    )
    return DashboardResponse(
        job_count=job_count,
        published_count=published_count,
        avg_qa_score=round(avg_qa, 3),
        total_clicks=m["clicks"],
        total_conversions=m["conversions"],
        total_orders=m["orders"],
        total_gmv=m["gmv"],
        chart=chart,
    )


def get_click(job_id: str | None = None) -> ClickResponse:
    m = _job_metrics(job_id)
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    chart = _echarts_line(
        "点击趋势",
        labels,
        [{"name": "点击", "type": "bar", "data": [int(m["clicks"] * (0.8 + i * 0.03)) for i in range(7)]}],
    )
    return ClickResponse(
        clicks=int(m["clicks"]),
        unique_clicks=int(m["unique_clicks"]),
        ctr=m["ctr"],
        records=[{"job_id": job_id or "all", "utm_campaign": f"seed_{job_id or 'all'}", "clicks": m["clicks"]}],
        chart=chart,
    )


def get_conversion(job_id: str | None = None) -> ConversionResponse:
    m = _job_metrics(job_id)
    chart = _echarts_line(
        "转化漏斗",
        ["曝光", "点击", "加购", "下单"],
        [{"name": "人数", "type": "bar", "data": [m["clicks"] * 5, m["clicks"], m["conversions"] * 2, m["conversions"]]}],
    )
    return ConversionResponse(
        conversions=int(m["conversions"]),
        conversion_rate=m["conversion_rate"],
        records=[{"job_id": job_id or "all", "conversions": m["conversions"]}],
        chart=chart,
    )


def get_order(job_id: str | None = None) -> OrderResponse:
    m = _job_metrics(job_id)
    chart = _echarts_line(
        "GMV 趋势",
        ["W1", "W2", "W3", "W4"],
        [{"name": "GMV", "type": "line", "data": [m["gmv"] * f for f in (0.6, 0.8, 0.9, 1.0)]}],
    )
    return OrderResponse(
        orders=int(m["orders"]),
        gmv=m["gmv"],
        records=[{"job_id": job_id or "all", "orders": m["orders"], "gmv": m["gmv"]}],
        chart=chart,
    )


def get_analysis(job_id: str | None = None) -> AnalysisResponse:
    _, avg_qa = _aggregate_jobs()
    m = _job_metrics(job_id)
    hints: list[str] = []
    if avg_qa < QA_PASS_THRESHOLD:
        hints.append(f"L2: 平均 QA {avg_qa:.2f} 低于阈值，优先优化脚本 hook")
    if m["ctr"] < 0.04:
        hints.append("L1: CTR 偏低，调整热点选题与封面")
    if m["conversion_rate"] < 0.08:
        hints.append("L3: 转化偏低，增加产品特写与 CTA 镜头")
    hints.extend([
        "L2: 前3秒钩子可 A/B 测试",
        "L7: 发布时段对齐平台流量高峰",
        "L8: 低效 SKU 降权，优先高 GMV 类目",
    ])
    chart = _echarts_line(
        "优化优先级",
        ["L1", "L2", "L3", "L4", "L7"],
        [{"name": "影响指数", "type": "bar", "data": [72, 88, 65, 40, 55]}],
    )
    return AnalysisResponse(
        summary=f"共分析 job={job_id or 'all'}；CTR={m['ctr']:.2%} CVR={m['conversion_rate']:.2%}",
        optimization_hints=hints,
        feedback_targets=["L1", "L2", "L3"],
        chart=chart,
    )
