from __future__ import annotations

from pydantic import BaseModel, Field


class PublishRequest(BaseModel):
    job_id: str
    video_path: str = ""
    title: str = ""
    cover_path: str = ""
    script_id: str | None = None
    platforms: list[str] = Field(default_factory=lambda: ["douyin"])
    blob_path: str = ""


class PublishedRecord(BaseModel):
    id: str
    job_id: str
    utm_campaign: str
    utm_content: str
    video_path: str
    blob_path: str
    publish_target: str
    platforms: list[str] = Field(default_factory=list)
    status: str
    created_at: str


class PublishResponse(BaseModel):
    published: PublishedRecord


class PublishedListResponse(BaseModel):
    items: list[PublishedRecord]
    total: int
