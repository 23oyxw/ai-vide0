from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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

app = FastAPI(
    title="AI Video Orchestrator",
    description="8-layer tooling coordination for e-commerce seeding videos",
    version=__version__,
)


class PipelineRequest(BaseModel):
    product_url: str | None = None
    demo_name: str = "product_ad"
    c4d_project: str | None = None
    layers: list[str] = Field(default_factory=lambda: list(DEFAULT_PIPELINE))
    force_qa_fail: bool = False


class PipelineResponse(BaseModel):
    job_id: str
    status: str
    pipeline_state: str
    results: list[dict[str, Any]]
    artifacts: dict[str, str]
    errors: list[str]
    retry_from: str | None = None
    optimization_hints: list[str] = Field(default_factory=list)


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


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "layers": list(LAYER_REGISTRY.keys()),
    }


@app.get("/tools/check")
async def tools_check() -> dict:
    import shutil
    from pathlib import Path

    return {
        "video_factory": {
            "path": str(settings.video_factory_path),
            "exists": settings.video_factory_path.exists(),
            "demos": list_demos(),
        },
        "ai_koubo": {
            "path": str(settings.ai_koubo_path),
            "exists": settings.ai_koubo_path.exists(),
        },
        "c4d": check_c4d(),
        "ffmpeg": {
            "path": str(settings.ffmpeg_path),
            "exists": settings.ffmpeg_path.exists(),
            "in_path": shutil.which("ffmpeg"),
        },
        "openclaw": {
            "bin": settings.openclaw_bin,
            "role": "dev_tooling_only",
            "note": "Not production scheduler; L5 uses Vercel Workflow in prod",
        },
    }


@app.get("/layers")
async def list_layers() -> dict:
    return {
        lid: {"name": layer.name, "description": layer.description}
        for lid, layer in LAYER_REGISTRY.items()
    }


@app.get("/monitor")
async def monitor() -> dict:
    """L6 QA monitor stub."""
    return {
        "status": "ok",
        "qa_score_avg": 0.85,
        "active_jobs": 0,
        "message": "RAG/QA monitor stub — connect Qdrant for full RAG",
    }


@app.post("/pipeline/run", response_model=PipelineResponse)
async def pipeline_run(req: PipelineRequest) -> PipelineResponse:
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

    return PipelineResponse(
        job_id=job_id,
        status=status,
        pipeline_state=pipeline_state.value,
        results=results,
        artifacts=ctx.artifacts,
        errors=ctx.errors,
        retry_from=retry_from,
        optimization_hints=optimization_hints,
    )


@app.post("/tools/video-factory/run")
async def tool_video_factory(demo_name: str = "product_ad") -> dict:
    return run_demo(demo_name)


@app.post("/tools/c4d/render")
async def tool_c4d_render(project_path: str, output_path: str | None = None) -> dict:
    return render_project(project_path, output_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.main:app",
        host=settings.orchestrator_host,
        port=settings.orchestrator_port,
        reload=True,
    )
