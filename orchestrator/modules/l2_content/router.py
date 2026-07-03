from __future__ import annotations

from fastapi import APIRouter, HTTPException

from orchestrator.modules.l2_content import service
from orchestrator.modules.l2_content.models import (
    GenerateScriptRequest,
    GenerateScriptResponse,
    ScriptGetResponse,
)
from orchestrator.schemas import ApiEnvelope, ok_envelope

router = APIRouter(prefix="/modules/l2-content", tags=["M2 内容创作"])


@router.post("/generate-script", response_model=ApiEnvelope[GenerateScriptResponse])
async def post_generate_script(req: GenerateScriptRequest) -> ApiEnvelope[GenerateScriptResponse]:
    data = await service.generate_script_record(req)
    return ok_envelope(data, layer="L2", job_id=data.script.id)


@router.get("/scripts/{script_id}", response_model=ApiEnvelope[ScriptGetResponse])
async def get_script(script_id: str) -> ApiEnvelope[ScriptGetResponse]:
    data = service.get_script(script_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Script {script_id} not found")
    return ok_envelope(data, layer="L2", job_id=script_id)
