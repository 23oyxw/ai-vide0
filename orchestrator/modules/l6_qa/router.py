from fastapi import APIRouter, Query

from orchestrator.modules.l6_qa import service
from orchestrator.modules.l6_qa.models import RulesResponse, ValidateRequest, ValidateResponse
from orchestrator.schemas import ApiEnvelope, MonitorCheck, MonitorData, MonitorRequest, ok_envelope

router = APIRouter(prefix="/modules/l6-qa", tags=["M6 质检闭环"])
legacy_router = APIRouter(tags=["M6 质检闭环 (legacy)"])


@router.post("/validate", response_model=ApiEnvelope[ValidateResponse])
async def post_validate(req: ValidateRequest) -> ApiEnvelope[ValidateResponse]:
    data = service.validate(req)
    return ok_envelope(data, layer="L6")


@router.get("/rules", response_model=ApiEnvelope[RulesResponse])
async def get_rules() -> ApiEnvelope[RulesResponse]:
    return ok_envelope(service.get_rules(), layer="L6")


def _monitor_payload(job_id: str | None) -> MonitorData:
    rules = service.get_rules()
    return MonitorData(
        qa_score_avg=0.85,
        active_jobs=0,
        checks=[
            MonitorCheck(name="visual_quality", passed=True, score=0.88, message="manifest QA"),
            MonitorCheck(name="content_safety", passed=True, score=0.90, message="keyword ban list"),
            MonitorCheck(
                name="structure_15s",
                passed=True,
                score=0.82,
                message=f"threshold={rules.pass_threshold}",
            ),
        ],
        message=f"RAG stub — {len(rules.prohibited_words)} prohibited keywords loaded",
    )


@legacy_router.get("/monitor")
async def legacy_monitor_get(job_id: str | None = Query(default=None)) -> ApiEnvelope[MonitorData]:
    return ok_envelope(_monitor_payload(job_id), layer="L6", job_id=job_id)


@legacy_router.post("/monitor")
async def legacy_monitor_post(req: MonitorRequest) -> ApiEnvelope[MonitorData]:
    return ok_envelope(_monitor_payload(req.job_id), layer="L6", job_id=req.job_id)
