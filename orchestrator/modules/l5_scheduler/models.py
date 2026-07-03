from __future__ import annotations

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    product_url: str | None = None
    demo_name: str = "post_production_15s_zhongcao"
    script_id: str | None = None
    storyboard_id: str | None = None
    render_job_id: str | None = None
    layers: list[str] = Field(default_factory=lambda: ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"])
    metadata: dict[str, str] = Field(default_factory=dict)


class JobRecord(BaseModel):
    job_id: str
    status: str
    pipeline_status: str = "pending"
    product_url: str = ""
    demo_name: str = ""
    script_id: str = ""
    storyboard_id: str = ""
    render_job_id: str = ""
    manifest_path: str = ""
    video_path: str = ""
    qa_score: str = ""
    publish_target: str = ""
    retry_count: int = 0
    errors: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class JobListResponse(BaseModel):
    jobs: list[JobRecord]
    total: int


class JobResponse(BaseModel):
    job: JobRecord
