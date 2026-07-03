from __future__ import annotations

from pydantic import BaseModel, Field


class RenderRequest(BaseModel):
    storyboard_id: str | None = None
    demo_name: str = "post_production_15s_zhongcao"
    c4d_project: str | None = None
    enable_c4d_scene2: bool = True
    job_id: str | None = None


class RenderJobRecord(BaseModel):
    job_id: str
    status: str
    demo_name: str
    manifest_path: str = ""
    video_path: str = ""
    output_dir: str = ""
    c4d_scene2_output: str = ""
    messages: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class RenderResponse(BaseModel):
    job: RenderJobRecord


class RenderStatusResponse(BaseModel):
    job: RenderJobRecord
