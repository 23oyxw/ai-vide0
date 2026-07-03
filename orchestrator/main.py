from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from orchestrator import __version__
from orchestrator.adapters.ai_koubo import check_health as koubo_health
from orchestrator.adapters.c4d import check_c4d, render_project
from orchestrator.adapters.video_factory import list_demos, run_demo
from orchestrator.config import settings
from orchestrator.job_store import job_store
from orchestrator.layers import LAYER_REGISTRY
from orchestrator.modules import MODULE_REGISTRY, mount_modules
from orchestrator.modules.l5_scheduler import service as scheduler_service
from orchestrator.pipeline_runner import run_pipeline
from orchestrator.pipeline_state import LAYER_INDEX
from orchestrator.schemas import (
    ApiEnvelope,
    HealthData,
    PipelineRunData,
    PipelineRunRequest,
    ToolsCheckData,
    err_envelope,
    ok_envelope,
)

app = FastAPI(
    title="AI Video Orchestrator",
    description="8-module tooling coordination for e-commerce seeding videos",
    version=__version__,
)

mount_modules(app)


def validate_layer_order(layers: list[str]) -> None:
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


@app.get("/modules")
async def list_modules() -> ApiEnvelope[dict[str, str]]:
    return ok_envelope(MODULE_REGISTRY, layer="L0")


@app.get("/tools/check", response_model=ApiEnvelope[ToolsCheckData])
async def tools_check() -> ApiEnvelope[ToolsCheckData]:
    import shutil

    koubo_status = await koubo_health()
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
                "url": settings.ai_koubo_url,
                **koubo_status,
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
                "note": "Not production scheduler; L5 uses module job queue",
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


@app.post("/pipeline/run", response_model=ApiEnvelope[PipelineRunData])
async def pipeline_run(req: PipelineRunRequest) -> ApiEnvelope[PipelineRunData]:
    validate_layer_order(req.layers)
    data = await run_pipeline(req)
    return ok_envelope(data, layer="L5", job_id=data.job_id)


@app.post("/tools/video-factory/run")
async def tool_video_factory(
    demo_name: str = "post_production_15s_zhongcao",
) -> ApiEnvelope[dict[str, Any]]:
    return ok_envelope(run_demo(demo_name), layer="L4")


@app.post("/tools/c4d/render")
async def tool_c4d_render(
    project_path: str,
    output_path: str | None = None,
) -> ApiEnvelope[dict[str, Any]]:
    return ok_envelope(render_project(project_path, output_path), layer="L4")


_job_events: dict[str, list[dict[str, Any]]] = {}


def _emit_event(job_id: str, event: str, data: dict[str, Any]) -> None:
    _job_events.setdefault(job_id, []).append(
        {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.post("/webhooks/render", response_model=ApiEnvelope[dict[str, Any]])
async def webhook_render(request: Request) -> ApiEnvelope[dict[str, Any]]:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    job_id = body.get("job_id", "unknown")
    status = body.get("status", "completed")
    artifact_url = body.get("artifact_url", "")
    error_msg = body.get("error", "")
    scheduler_service.update_job(
        job_id,
        {
            "status": "published" if status == "completed" else "error",
            "render_status": status,
            "artifact_url": artifact_url,
            "render_error": error_msg,
        },
    )
    _emit_event(
        job_id,
        "render_complete",
        {"job_id": job_id, "status": status, "artifact_url": artifact_url},
    )
    return ok_envelope({"job_id": job_id, "acknowledged": True}, layer="L5", job_id=job_id)


@app.get("/jobs/{job_id}", response_model=ApiEnvelope[dict[str, Any]])
async def get_job_status(job_id: str = Path(..., min_length=1)) -> ApiEnvelope[dict[str, Any]]:
    data = scheduler_service.get_job(job_id)
    if not data:
        return err_envelope(code="not_found", message=f"Job {job_id} not found")
    return ok_envelope(data.job.model_dump(), layer="L5", job_id=job_id)


@app.get("/jobs/{job_id}/stream")
async def stream_job_events(job_id: str = Path(..., min_length=1)) -> StreamingResponse:
    async def event_generator():
        history = _job_events.get(job_id, [])
        for evt in history:
            yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'])}\n\n"
        yield f"event: connected\ndata: {json.dumps({'job_id': job_id})}\n\n"
        start_index = len(history)
        while True:
            await asyncio.sleep(1)
            current = _job_events.get(job_id, [])
            for evt in current[start_index:]:
                yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'])}\n\n"
            start_index = len(current)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.main:app",
        host=settings.orchestrator_host,
        port=settings.orchestrator_port,
        reload=True,
    )
