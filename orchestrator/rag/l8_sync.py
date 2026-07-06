from __future__ import annotations

from typing import Any

from orchestrator.rag.indexes import get_stub_index
from orchestrator.rag.pipeline import run_ingestion_pipeline
from orchestrator.rag.readers import documents_from_texts, enrich_metadata


def build_l8_hierarchical_text(job_id: str | None = None) -> str:
    """TreeIndex 替代：L8 指标分层文本（根 → 分支 → 叶子）。"""
    from orchestrator.modules.l8_analytics import service as l8

    dash = l8.get_dashboard(job_id)
    click = l8.get_click(job_id)
    conv = l8.get_conversion(job_id)
    order = l8.get_order(job_id)
    analysis = l8.get_analysis(job_id)

    lines = [
        f"# 运营总览 job={job_id or 'all'}",
        f"## 一级：核心 KPI",
        f"- 任务数: {dash.job_count} | 已发布: {dash.published_count} | 平均 QA: {dash.avg_qa_score}",
        f"- 总点击: {dash.total_clicks} | 转化: {dash.total_conversions} | 订单: {dash.total_orders} | GMV: {dash.total_gmv}",
        f"## 二级：流量",
        f"- CTR: {click.ctr:.2%} | 点击: {click.clicks} | 独立点击: {click.unique_clicks}",
        f"## 二级：转化",
        f"- CVR: {conv.conversion_rate:.2%} | 转化数: {conv.conversions}",
        f"## 二级：订单",
        f"- 订单: {order.orders} | GMV: {order.gmv}",
        f"## 三级：优化建议",
    ]
    lines.extend(f"- {h}" for h in analysis.optimization_hints[:8])
    lines.append(f"## 摘要\n{analysis.summary}")
    return "\n".join(lines)


def sync_l8_to_rag(job_id: str | None = None) -> dict[str, Any]:
    text = build_l8_hierarchical_text(job_id)
    documents = enrich_metadata(
        documents_from_texts(
            [text],
            metadata={"job_id": job_id or "all", "source_type": "l8_analytics"},
        ),
        source_type="l8_analytics",
        category="数据报表",
    )
    nodes = run_ingestion_pipeline(
        documents, source_type="l8_analytics", category="数据报表", splitter="hierarchical"
    )
    added = get_stub_index().add_nodes(nodes)
    return {
        "job_id": job_id,
        "nodes_added": added,
        "preview_chars": len(text),
        "engine": "stub_tree_l8",
    }
