from __future__ import annotations

from fastapi import APIRouter, HTTPException

from orchestrator.modules.l5_scheduler import service
from orchestrator.modules.l5_scheduler.models import JobCreateRequest, JobListResponse, JobResponse
from orchestrator.schemas import ApiEnvelope, ok_envelope

router = APIRouter(prefix="/modules/l5-scheduler", tags=["M5 调度中枢"])


@router.get("/jobs", response_model=ApiEnvelope[JobListResponse])
async def list_jobs() -> ApiEnvelope[JobListResponse]:
    return ok_envelope(service.list_jobs(), layer="L5")


@router.post("/jobs", response_model=ApiEnvelope[JobResponse])
async def create_job(req: JobCreateRequest) -> ApiEnvelope[JobResponse]:
    data = service.create_job(req)
    return ok_envelope(data, layer="L5", job_id=data.job.job_id)


@router.get("/jobs/{job_id}", response_model=ApiEnvelope[JobResponse])
async def get_job(job_id: str) -> ApiEnvelope[JobResponse]:
    data = service.get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return ok_envelope(data, layer="L5", job_id=job_id)


@router.post("/jobs/{job_id}/retry", response_model=ApiEnvelope[JobResponse])
async def retry_job(job_id: str) -> ApiEnvelope[JobResponse]:
    data = service.retry_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return ok_envelope(data, layer="L5", job_id=job_id)


@router.post("/jobs/{job_id}/cancel", response_model=ApiEnvelope[JobResponse])
async def cancel_job(job_id: str) -> ApiEnvelope[JobResponse]:
    data = service.cancel_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return ok_envelope(data, layer="L5", job_id=job_id)
