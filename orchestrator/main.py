from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from orchestrator import __version__
from orchestrator.adapters.c4d import check_c4d, render_project
from orchestrator.adapters.video_factory import list_demos, run_demo
from orchestrator.config import settings
from orchestrator.layers import DEFAULT_PIPELINE, LAYER_REGISTRY
from orchestrator.layers.base import LayerContext
from orchestrator.pipeline_state import (
    LAYER_INDEX,
    QA_PASS_THRESHOLD,
    QA_RETRY_FROM,
    PipelineState,
)
from orchestrator.schemas import (
    ApiEnvelope,
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

app = FastAPI(
    title="AI Video Orchestrator",
    description="8-layer tooling coordination for e-commerce seeding videos",
    version=__version__,
)


def validate_layer_order(layers: list[str]) -> None:
    """Enforce strict L1->L8 dependency: ordered subsequence only."""
    prev = -1
    for lid in layers:
        if lid not in LAYER_INDEX:
            raise HTTPException(status_code=400, detail=f"Unknown layer: {lid}")
        idx = LAYER_INDEX[lid]
        if idx <= prev:
            raise HTTPException(
                status_code=400,
                detail=f"Layer order violation at {lid}: must follow L1->L8 DAG",
            )
        prev = idx


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    envelope = err_envelope(
        code=f"http_{exc.status_code}",
        message=str(exc.detail),
        detail=exc.detail if isinstance(exc.detail, dict) else None,
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())


@app.get("/health", response_model=ApiEnvelope[HealthData])
async def health() -> ApiEnvelope[HealthData]:
    return ok_envelope(
        HealthData(
            status="ok",
            version=__version__,
            layers=list(LAYER_REGISTRY.keys()),
        ),
        layer="L0",
    )


@app.get("/tools/check", response_model=ApiEnvelope[ToolsCheckData])
async def tools_check() -> ApiEnvelope[ToolsCheckData]:
    import shutil

    return ok_envelope(
        ToolsCheckData(
            video_factory={
                "path": str(settings.video_factory_path),
                "exists": settings.video_factory_path.exists(),
                "demos": list_demos(),
            },
            ai_koubo={
                "path": str(settings.ai_koubo_path),
                "exists": settings.ai_koubo_path.exists(),
            },
            c4d=check_c4d(),
            ffmpeg={
                "path": str(settings.ffmpeg_path),
                "exists": settings.ffmpeg_path.exists(),
                "in_path": shutil.which("ffmpeg"),
            },
            openclaw={
                "bin": settings.openclaw_bin,
                "role": "dev_tooling_only",
                "note": "Not production scheduler; L5 uses Vercel Workflow in prod",
            },
        ),
        layer="L0",
    )


@app.get("/layers")
async def list_layers() -> ApiEnvelope[dict[str, dict[str, str]]]:
    return ok_envelope(
        {
            lid: {"name": layer.name, "description": layer.description}
            for lid, layer in LAYER_REGISTRY.items()
        },
        layer="L0",
    )


@app.get("/agent/crawler", response_model=ApiEnvelope[CrawlerData])
async def agent_crawler_get(
    product_url: str | None = Query(default=None),
) -> ApiEnvelope[CrawlerData]:
    req = CrawlerRequest(product_url=product_url)
    return await agent_crawler(req)


@app.post("/agent/crawler", response_model=ApiEnvelope[CrawlerData])
async def agent_crawler(req: CrawlerRequest) -> ApiEnvelope[CrawlerData]:
    job_id = req.job_id or str(uuid.uuid4())[:8]
    ctx = LayerContext(job_id=job_id, product_url=req.product_url)
    await LAYER_REGISTRY["L1"].run(ctx)
    url = ctx.artifacts.get("crawled_url", req.product_url or "https://example.com/product")

    return ok_envelope(
        CrawlerData(
            crawled_url=url,
            selection_card=SelectionCard(
                title="Demo 选品卡片",
                pain_points=["痛点 A：功效不明显", "痛点 B：价格敏感"],
                category="beauty",
            ),
            competitor_count=len(req.competitor_urls),
            rag_candidates=[f"rag_candidate_{job_id}"],
        ),
        layer="L1",
        job_id=job_id,
    )


def _monitor_payload(job_id: str | None = None) -> MonitorData:
    return MonitorData(
        qa_score_avg=0.85,
        active_jobs=0,
        checks=[
            MonitorCheck(
                name="visual_quality",
                passed=True,
                score=0.88,
                message="画面清晰度 stub 通过",
            ),
            MonitorCheck(
                name="script_intellisafe",
                passed=True,
                score=0.90,
                message="脚本合规 stub 通过",
            ),
            MonitorCheck(
                name="structure_15s",
                passed=True,
                score=0.82,
                message="15 秒结构 stub 通过",
            ),
        ],
        message="RAG/QA monitor stub — connect Qdrant for full RAG",
    )


@app.get("/monitor", response_model=ApiEnvelope[MonitorData])
async def monitor_get(
    job_id: str | None = Query(default=None),
) -> ApiEnvelope[MonitorData]:
    return ok_envelope(_monitor_payload(job_id), layer="L6", job_id=job_id)


@app.post("/monitor", response_model=ApiEnvelope[MonitorData])
async def monitor_post(req: MonitorRequest) -> ApiEnvelope[MonitorData]:
    return ok_envelope(_monitor_payload(req.job_id), layer="L6", job_id=req.job_id)


def _data_click(job_id: str | None) -> DataClickData:
    return DataClickData(
        clicks=1280,
        unique_clicks=960,
        ctr=0.042,
        records=[
            {
                "job_id": job_id or "demo",
                "utm_campaign": "seed_video",
                "clicks": 1280,
            }
        ],
    )


@app.get("/data/click", response_model=ApiEnvelope[DataClickData])
async def data_click_get(
    job_id: str | None = Query(default=None),
    utm_campaign: str | None = Query(default=None),
) -> ApiEnvelope[DataClickData]:
    return ok_envelope(_data_click(job_id), layer="L8", job_id=job_id)


@app.post("/data/click", response_model=ApiEnvelope[DataClickData])
async def data_click_post(req: DataClickQuery) -> ApiEnvelope[DataClickData]:
    return ok_envelope(_data_click(req.job_id), layer="L8", job_id=req.job_id)


def _data_conversion(job_id: str | None) -> DataConversionData:
    return DataConversionData(
        conversions=86,
        conversion_rate=0.089,
        records=[{"job_id": job_id or "demo", "conversions": 86}],
    )


@app.get("/data/conversion", response_model=ApiEnvelope[DataConversionData])
async def data_conversion_get(
    job_id: str | None = Query(default=None),
) -> ApiEnvelope[DataConversionData]:
    return ok_envelope(_data_conversion(job_id), layer="L8", job_id=job_id)


@app.post("/data/conversion", response_model=ApiEnvelope[DataConversionData])
async def data_conversion_post(
    req: DataConversionQuery,
) -> ApiEnvelope[DataConversionData]:
    return ok_envelope(_data_conversion(req.job_id), layer="L8", job_id=req.job_id)


def _data_order(job_id: str | None) -> DataOrderData:
    return DataOrderData(
        orders=42,
        gmv=12880.50,
        records=[{"job_id": job_id or "demo", "orders": 42, "gmv": 12880.50}],
    )


@app.get("/data/order", response_model=ApiEnvelope[DataOrderData])
async def data_order_get(
    job_id: str | None = Query(default=None),
) -> ApiEnvelope[DataOrderData]:
    return ok_envelope(_data_order(job_id), layer="L8", job_id=job_id)


@app.post("/data/order", response_model=ApiEnvelope[DataOrderData])
async def data_order_post(req: DataOrderQuery) -> ApiEnvelope[DataOrderData]:
    return ok_envelope(_data_order(req.job_id), layer="L8", job_id=req.job_id)


@app.get("/data/analysis", response_model=ApiEnvelope[DataAnalysisData])
async def data_analysis_get(
    job_id: str | None = Query(default=None),
) -> ApiEnvelope[DataAnalysisData]:
    return ok_envelope(
        DataAnalysisData(
            summary="L8 分析 stub：点击/转化/订单汇总",
            optimization_hints=[
                "提高前3秒 hook 强度 -> 反馈 L2 脚本模板",
                "L1: 低效 SKU 降权，优先高转化类目",
            ],
            feedback_targets=["L1", "L2", "L3"],
        ),
        layer="L8",
        job_id=job_id,
    )


@app.post("/data/analysis", response_model=ApiEnvelope[DataAnalysisData])
async def data_analysis_post(
    req: DataAnalysisRequest,
) -> ApiEnvelope[DataAnalysisData]:
    return ok_envelope(
        DataAnalysisData(
            summary="L8 分析 stub：基于提交 metrics 生成优化建议",
            optimization_hints=[
                "提高前3秒 hook 强度 -> 反馈 L2 脚本模板",
                "L3: 增加产品特写镜头占比",
            ],
            feedback_targets=["L1", "L2", "L3"],
        ),
        layer="L8",
        job_id=req.job_id,
    )


@app.post("/pipeline/run", response_model=ApiEnvelope[PipelineRunData])
async def pipeline_run(req: PipelineRunRequest) -> ApiEnvelope[PipelineRunData]:
    validate_layer_order(req.layers)

    job_id = str(uuid.uuid4())[:8]
    ctx = LayerContext(
        job_id=job_id,
        product_url=req.product_url,
        demo_name=req.demo_name,
        c4d_project=req.c4d_project,
        metadata={"force_qa_fail": req.force_qa_fail},
    )

    pipeline_state = PipelineState.RUNNING
    retry_from: str | None = None
    optimization_hints: list[str] = []
    results: list[dict[str, Any]] = []
    ran_l7 = False
    l7_ok = False

    for lid in req.layers:
        if lid == "L4":
            pipeline_state = PipelineState.L4_RENDER

        layer = LAYER_REGISTRY[lid]
        result = await layer.run(ctx)
        results.append(result.model_dump())

        if lid == "L6":
            score_raw = ctx.artifacts.get("qa_score", "1")
            try:
                score = float(score_raw)
            except ValueError:
                score = 0.0

            qa_failed = (
                result.status == "error"
                or req.force_qa_fail
                or score < QA_PASS_THRESHOLD
            )
            if qa_failed:
                pipeline_state = PipelineState.QA_FAILED
                retry_from = QA_RETRY_FROM
                ctx.errors.append(
                    f"L6 QA failed (score={score}); retry_from={QA_RETRY_FROM}"
                )
                break

        if lid == "L7":
            ran_l7 = True
            l7_ok = result.status == "ok"

        if result.status == "error" and lid != "L6":
            pipeline_state = PipelineState.ERROR
            break

        if lid != "L4" and pipeline_state == PipelineState.L4_RENDER:
            pipeline_state = PipelineState.RUNNING

    if pipeline_state == PipelineState.QA_FAILED:
        status = "qa_failed"
    elif ctx.errors or pipeline_state == PipelineState.ERROR:
        status = "error"
        if pipeline_state not in (PipelineState.QA_FAILED, PipelineState.ERROR):
            pipeline_state = PipelineState.ERROR
    else:
        status = "ok"
        if ran_l7 and l7_ok:
            pipeline_state = PipelineState.PUBLISHED
        if "L8" in req.layers and results and results[-1].get("layer_id") == "L8":
            pipeline_state = PipelineState.ANALYZED
            raw_hints = ctx.metadata.get("optimization_hints")
            if isinstance(raw_hints, list):
                optimization_hints = [str(h) for h in raw_hints]

    layer_results = [LayerResultPayload.model_validate(r) for r in results]

    return ok_envelope(
        PipelineRunData(
            job_id=job_id,
            status=status,
            pipeline_state=pipeline_state.value,
            layers=list(req.layers),
            layer_results=layer_results,
            artifacts=ctx.artifacts,
            errors=ctx.errors,
            retry_from=retry_from,
            optimization_hints=optimization_hints,
        ),
        layer="L5",
        job_id=job_id,
    )


@app.post("/tools/video-factory/run")
async def tool_video_factory(demo_name: str = "product_ad") -> ApiEnvelope[dict[str, Any]]:
    return ok_envelope(run_demo(demo_name), layer="L4")


@app.post("/tools/c4d/render")
async def tool_c4d_render(
    project_path: str,
    output_path: str | None = None,
) -> ApiEnvelope[dict[str, Any]]:
    return ok_envelope(render_project(project_path, output_path), layer="L4")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.main:app",
        host=settings.orchestrator_host,
        port=settings.orchestrator_port,
        reload=True,
    )
