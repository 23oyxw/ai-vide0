from __future__ import annotations

from orchestrator.job_store import job_store
from orchestrator.modules.common import new_id, utc_now_iso
from orchestrator.modules.l5_scheduler.models import (
    JobCreateRequest,
    JobListResponse,
    JobRecord,
    JobResponse,
)


def _to_record(job_id: str, raw: dict) -> JobRecord:
    return JobRecord(
        job_id=job_id,
        status=str(raw.get("status", "unknown")),
        pipeline_status=str(raw.get("pipeline_status", raw.get("status", "unknown"))),
        product_url=str(raw.get("product_url", "")),
        demo_name=str(raw.get("demo_name", "")),
        script_id=str(raw.get("script_id", "")),
        storyboard_id=str(raw.get("storyboard_id", "")),
        render_job_id=str(raw.get("render_job_id", "")),
        manifest_path=str(raw.get("manifest_path", "")),
        video_path=str(raw.get("video_path", "")),
        qa_score=str(raw.get("qa_score", "")),
        publish_target=str(raw.get("publish_target", "")),
        retry_count=int(raw.get("retry_count", 0)),
        errors=list(raw.get("errors", [])),
        created_at=str(raw.get("created_at", raw.get("updated_at", ""))),
        updated_at=str(raw.get("updated_at", "")),
    )


def create_job(req: JobCreateRequest) -> JobResponse:
    job_id = new_id("j")
    now = utc_now_iso()
    state = {
        "status": "pending",
        "pipeline_status": "pending",
        "product_url": req.product_url or "",
        "demo_name": req.demo_name,
        "script_id": req.script_id or "",
        "storyboard_id": req.storyboard_id or "",
        "render_job_id": req.render_job_id or "",
        "layers": req.layers,
        "metadata": req.metadata,
        "retry_count": 0,
        "errors": [],
        "created_at": now,
    }
    job_store.save(job_id, state)
    raw = job_store.load(job_id) or state
    return JobResponse(job=_to_record(job_id, raw))


def list_jobs(limit: int = 50) -> JobListResponse:
    ids = job_store.list_jobs()[:limit]
    jobs: list[JobRecord] = []
    for job_id in ids:
        raw = job_store.load(job_id)
        if raw:
            jobs.append(_to_record(job_id, raw))
    return JobListResponse(jobs=jobs, total=len(jobs))


def get_job(job_id: str) -> JobResponse | None:
    raw = job_store.load(job_id)
    if not raw:
        return None
    return JobResponse(job=_to_record(job_id, raw))


def update_job(job_id: str, patch: dict) -> JobResponse | None:
    raw = job_store.load(job_id)
    if not raw:
        return None
    raw.update(patch)
    job_store.save(job_id, raw)
    return JobResponse(job=_to_record(job_id, raw))


def retry_job(job_id: str) -> JobResponse | None:
    raw = job_store.load(job_id)
    if not raw:
        return None
    if raw.get("status") == "cancelled":
        return JobResponse(job=_to_record(job_id, raw))
    raw["retry_count"] = int(raw.get("retry_count", 0)) + 1
    raw["status"] = "pending"
    raw["pipeline_status"] = "retry_scheduled"
    raw.setdefault("errors", []).append(f"retry #{raw['retry_count']} at {utc_now_iso()}")
    job_store.save(job_id, raw)
    return JobResponse(job=_to_record(job_id, raw))


def cancel_job(job_id: str) -> JobResponse | None:
    raw = job_store.load(job_id)
    if not raw:
        return None
    raw["status"] = "cancelled"
    raw["pipeline_status"] = "cancelled"
    job_store.save(job_id, raw)
    return JobResponse(job=_to_record(job_id, raw))
