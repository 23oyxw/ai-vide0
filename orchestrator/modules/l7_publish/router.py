from __future__ import annotations

from fastapi import APIRouter

from orchestrator.modules.l7_publish import service
from orchestrator.modules.l7_publish.models import PublishRequest, PublishedListResponse, PublishResponse
from orchestrator.schemas import ApiEnvelope, ok_envelope

router = APIRouter(prefix="/modules/l7-publish", tags=["M7 发布输出"])


@router.post("/publish", response_model=ApiEnvelope[PublishResponse])
async def post_publish(req: PublishRequest) -> ApiEnvelope[PublishResponse]:
    data = await service.publish(req)
    return ok_envelope(data, layer="L7", job_id=req.job_id)


@router.get("/published", response_model=ApiEnvelope[PublishedListResponse])
async def get_published() -> ApiEnvelope[PublishedListResponse]:
    return ok_envelope(service.list_published(), layer="L7")
