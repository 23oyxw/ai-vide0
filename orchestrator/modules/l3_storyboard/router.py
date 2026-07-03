from __future__ import annotations

from fastapi import APIRouter, HTTPException

from orchestrator.modules.l3_storyboard import service
from orchestrator.modules.l3_storyboard.models import BuildStoryboardRequest, StoryboardResponse
from orchestrator.schemas import ApiEnvelope, ok_envelope

router = APIRouter(prefix="/modules/l3-storyboard", tags=["M3 镜头重构"])


@router.post("/build-from-script", response_model=ApiEnvelope[StoryboardResponse])
async def post_build(req: BuildStoryboardRequest) -> ApiEnvelope[StoryboardResponse]:
    data = service.build_from_script(req)
    return ok_envelope(data, layer="L3", job_id=data.storyboard.id)


@router.get("/storyboard/{storyboard_id}", response_model=ApiEnvelope[StoryboardResponse])
async def get_storyboard(storyboard_id: str) -> ApiEnvelope[StoryboardResponse]:
    data = service.get_storyboard(storyboard_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Storyboard {storyboard_id} not found")
    return ok_envelope(data, layer="L3", job_id=storyboard_id)
