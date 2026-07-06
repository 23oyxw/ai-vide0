from __future__ import annotations

from pydantic import BaseModel, Field


class StoryboardSegment(BaseModel):
    code: str
    title: str
    start: float
    end: float
    duration: float
    narration: str = ""
    visual: str = ""


class BuildStoryboardRequest(BaseModel):
    script_id: str | None = None
    demo_name: str = "post_production_15s_zhongcao"
    video_style: str = "real"
    segments_override: list[StoryboardSegment] = Field(default_factory=list)
    script_text: str = ""


class StoryboardRecord(BaseModel):
    id: str
    demo_name: str
    title: str
    duration_target_sec: float
    width: int = 1080
    height: int = 1920
    fps: int = 30
    segments: list[StoryboardSegment]
    yaml_path: str = ""
    created_at: str


class StoryboardResponse(BaseModel):
    storyboard: StoryboardRecord
