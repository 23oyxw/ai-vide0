from __future__ import annotations

from fastapi import APIRouter, HTTPException

from orchestrator.modules.l4_render import service
from orchestrator.modules.l4_render.models import RenderRequest, RenderResponse, RenderStatusResponse
from orchestrator.schemas import ApiEnvelope, ok_envelope

router = APIRouter(prefix="/modules/l4-render", tags=["M4 渲染合成"])


@router.post("/render", response_model=ApiEnvelope[RenderResponse])
async def post_render(req: RenderRequest) -> ApiEnvelope[RenderResponse]:
    data = await service.start_render(req)
    return ok_envelope(data, layer="L4", job_id=data.job.job_id)


@router.get("/render/{job_id}/status", response_model=ApiEnvelope[RenderStatusResponse])
async def get_render_status(job_id: str) -> ApiEnvelope[RenderStatusResponse]:
    data = service.get_render_status(job_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Render job {job_id} not found")
    return ok_envelope(data, layer="L4", job_id=job_id)
