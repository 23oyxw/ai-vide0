from __future__ import annotations

from pydantic import BaseModel, Field


class RenderRequest(BaseModel):
    storyboard_id: str | None = None
    demo_name: str = "post_production_15s_zhongcao"
    video_style: str = "real"  # real | product | 3d | unbox | compare
    c4d_project: str | None = None
    enable_c4d_scene2: bool = True
    enable_cogvideo: bool = False
    # cogvideo_mode: 'sync' | 'async' | 'auto' (auto = try sync, fallback to async)
    cogvideo_mode: str = "auto"
    cogvideo_prompt: str = ""
    job_id: str | None = None
    crawled_image_urls: list[str] = Field(default_factory=list)


class RenderJobRecord(BaseModel):
    job_id: str
    status: str
    demo_name: str
    manifest_path: str = ""
    video_path: str = ""
    output_dir: str = ""
    c4d_scene2_output: str = ""
    cogvideo_task_id: str = ""
    cogvideo_video_url: str = ""
    cogvideo_local_path: str = ""
    messages: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class RenderResponse(BaseModel):
    job: RenderJobRecord


class RenderStatusResponse(BaseModel):
    job: RenderJobRecord
