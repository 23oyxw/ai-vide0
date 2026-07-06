from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Path, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from orchestrator.http_response import UTF8JSONResponse
# Ensure HTTPX clients inject Authorization when adapters still use literal placeholders
import orchestrator.adapters._client_shim  # noqa: F401  (shim applies on import)

from orchestrator import __version__
from orchestrator.adapters.ai_koubo import check_health as koubo_health
from orchestrator.adapters.c4d import check_c4d, render_project
from orchestrator.adapters.cogvideo_client2 import check_cogvideo
from orchestrator.adapters.video_factory import list_demos, run_demo
from orchestrator.adapters.zhipu_client2 import check_health as zhipu_health
from orchestrator.config import settings
from orchestrator.job_store import job_store
from orchestrator.layers import LAYER_REGISTRY
from orchestrator.modules import MODULE_REGISTRY, mount_modules
from orchestrator.modules.l5_scheduler import service as scheduler_service
from orchestrator.modules.l8_analytics.models import MetricsRecordRequest
from orchestrator.modules.l8_analytics import service as l8_analytics_service
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

@asynccontextmanager
async def lifespan(_app: FastAPI):
    import logging

    log = logging.getLogger(__name__)
    from orchestrator.adapters.l8_store import init_local_store

    try:
        source = init_local_store()
        log.info("L8 metrics store initialized: %s", source)
    except Exception as exc:
        log.warning("L8 store init skipped: %s", exc)

    if settings.rag_bootstrap_on_startup:
        from orchestrator.rag.service import rag_service

        try:
            rag_service.bootstrap()
        except Exception as exc:
            log.warning("RAG bootstrap skipped: %s", exc)
    yield


app = FastAPI(
    title="AI Video Orchestrator",
    description="8-module tooling coordination for e-commerce seeding videos",
    version=__version__,
    lifespan=lifespan,
    default_response_class=UTF8JSONResponse,
)

mount_modules(app)

# CORS — allow static frontends (Gitee Pages, Vercel, localhost) to call orchestrator directly
# Note: allow_credentials=False is required when using allow_origins=["*"] per CORS spec
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return UTF8JSONResponse(status_code=exc.status_code, content=envelope.model_dump())


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
            zhipu={
                "text_model": settings.zhipu_text_model,
                "reasoning_model": settings.zhipu_reasoning_model,
                "vision_model": settings.zhipu_vision_model,
                "configured": bool(settings.zhipu_api_key),
            },
            cogvideo=check_cogvideo(),
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
    """Run pipeline with FFmpeg fast video generation (2-5s for L4)."""
    validate_layer_order(req.layers)
    data = await run_pipeline(req)
    return ok_envelope(data, layer="L5", job_id=data.job_id)


@app.get("/pipeline/status/{job_id}", response_model=ApiEnvelope[dict])
async def pipeline_status(job_id: str = Path(..., min_length=1)) -> ApiEnvelope[dict]:
    """Poll pipeline job status — returns full result when done."""
    from orchestrator.modules.l5_scheduler import service as l5
    job = l5.get_job(job_id)
    if not job:
        return err_envelope(code="not_found", message=f"Job {job_id} not found")
    return ok_envelope(job.job.model_dump(), layer="L5", job_id=job_id)


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


from orchestrator.event_store import append_event, get_events, tail_events


def _emit_event(job_id: str, event: str, data: dict[str, Any]) -> None:
    # Append event to persistent per-job events file (NDJSON)
    try:
        append_event(job_id, event, data)
    except Exception:
        # Best-effort: swallow errors to avoid breaking pipeline flow
        pass


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


@app.post("/webhooks/analytics", response_model=ApiEnvelope[dict[str, Any]])
async def webhook_analytics(request: Request) -> ApiEnvelope[dict[str, Any]]:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    job_id = body.get("job_id", "all")
    req = MetricsRecordRequest(
        job_id=job_id,
        metric_date=body.get("metric_date"),
        clicks=int(body.get("clicks", 0)),
        unique_clicks=int(body.get("unique_clicks", 0)),
        conversions=int(body.get("conversions", 0)),
        orders=int(body.get("orders", 0)),
        gmv=float(body.get("gmv", 0)),
    )
    result = l8_analytics_service.record_metrics(req)
    _emit_event(
        job_id,
        "analytics_ingest",
        {"job_id": job_id, "backend": result.backend, "metric_date": result.metric_date},
    )
    return ok_envelope(result.model_dump(), layer="L8", job_id=job_id)


@app.get("/jobs/{job_id}", response_model=ApiEnvelope[dict[str, Any]])
async def get_job_status(job_id: str = Path(..., min_length=1)) -> ApiEnvelope[dict[str, Any]]:
    data = scheduler_service.get_job(job_id)
    if not data:
        return err_envelope(code="not_found", message=f"Job {job_id} not found")
    return ok_envelope(data.job.model_dump(), layer="L5", job_id=job_id)


@app.get("/tools/zhipu/health")
async def tool_zhipu_health() -> ApiEnvelope[dict[str, Any]]:
    return ok_envelope(await zhipu_health(), layer="L0")


@app.post("/tools/zhipu/script")
async def tool_zhipu_script(
    topic: str = "种草产品",
    product_url: str | None = None,
) -> ApiEnvelope[dict[str, Any]]:
    """Quick test: generate a script via Zhipu GLM-4-Flash."""
    from orchestrator.adapters.zhipu_client import generate_script as zhipu_gen
    result = await zhipu_gen(product_url=product_url, raw_text=topic)
    return ok_envelope(result, layer="L2")


@app.post("/tools/cogvideo/generate")
async def tool_cogvideo_generate(
    prompt: str,
    image_url: str | None = None,
    duration: int = 5,
) -> ApiEnvelope[dict[str, Any]]:
    """Submit + poll a CogVideoX-3 generation (one-shot)."""
    from orchestrator.adapters.cogvideo_client2 import generate_clip
    result = await generate_clip(prompt=prompt, image_url=image_url, duration=duration)
    return ok_envelope(result, layer="L4")


@app.get("/jobs/{job_id}/stream")
async def stream_job_events(job_id: str = Path(..., min_length=1)) -> StreamingResponse:
    async def event_generator():
        history = get_events(job_id)
        for evt in history:
            yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'])}\n\n"
        yield f"event: connected\ndata: {json.dumps({'job_id': job_id})}\n\n"
        start_index = len(history)
        while True:
            await asyncio.sleep(1)
            current = get_events(job_id)
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


@app.get("/video/{job_id}")
async def serve_video(job_id: str = Path(..., min_length=1)):
    """Serve generated video: FFmpeg output first, then render job path, then video-factory."""
    # 1. FFmpeg output (fast, always 5s, reliable)
    ffmpeg_path = settings.data_root / "l4" / "renders" / job_id / "output.mp4"
    if ffmpeg_path.exists():
        return FileResponse(ffmpeg_path, media_type="video/mp4", filename=f"{job_id}.mp4")

    # 2. Render job recorded path
    from orchestrator.modules.l4_render.service import get_render_status
    render = get_render_status(job_id)
    if render and render.job.video_path:
        path = Path(render.job.video_path)
        if path.exists():
            return FileResponse(path, media_type="video/mp4", filename=path.name)

    # 3. Latest video-factory output (fallback)
    vf_output = settings.video_factory_path / "output"
    if vf_output.exists():
        for demo_dir in sorted(vf_output.iterdir(), reverse=True):
            if demo_dir.is_dir():
                for run_dir in sorted(demo_dir.iterdir(), reverse=True):
                    final = run_dir / "final.mp4"
                    if final.exists():
                        return FileResponse(final, media_type="video/mp4", filename="final.mp4")

    raise HTTPException(status_code=404, detail="No video found for this job")


@app.get("/images/{job_id}")
async def list_product_images(job_id: str = Path(..., min_length=1)):
    """List product images generated for a pipeline job."""
    img_dir = settings.data_root / "l4" / "renders" / job_id
    if not img_dir.exists():
        return err_envelope(code="not_found", message="No images for this job")
    images = sorted(img_dir.glob("product_*.jpg"))
    return ok_envelope({
        "job_id": job_id,
        "count": len(images),
        "images": [f"/image/{job_id}/{p.name}" for p in images],
    }, layer="L4", job_id=job_id)


@app.get("/image/{job_id}/{filename}")
async def serve_product_image(job_id: str, filename: str):
    """Serve a single product image."""
    img_path = settings.data_root / "l4" / "renders" / job_id / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(img_path, media_type="image/jpeg")


@app.post("/upload/product-image")
async def upload_product_image(
    job_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload a product image to be used in video rendering."""
    from fastapi import Form, UploadFile, File
    img_dir = settings.data_root / "l4" / "renders" / job_id
    img_dir.mkdir(parents=True, exist_ok=True)
    # Save uploaded file
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    idx = len(list(img_dir.glob("uploaded_*")))
    path = img_dir / f"uploaded_{idx}{ext}"
    content = await file.read()
    path.write_bytes(content)
    return ok_envelope({
        "job_id": job_id,
        "path": str(path),
        "size": len(content),
        "index": idx,
    }, layer="L4", job_id=job_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.main:app",
        host=settings.orchestrator_host,
        port=settings.orchestrator_port,
        reload=True,
    )
