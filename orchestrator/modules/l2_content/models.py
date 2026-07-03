from __future__ import annotations

from pydantic import BaseModel, Field


class ScriptSegment(BaseModel):
    code: str
    role: str
    start_sec: float
    end_sec: float
    duration_sec: float
    narration: str


class GenerateScriptRequest(BaseModel):
    product_url: str | None = None
    topic: str = ""
    raw_text: str = ""
    style: str = "种草短视频"
    topic_id: str | None = None


class ScriptRecord(BaseModel):
    id: str
    full_text: str
    segments: list[ScriptSegment]
    duration_sec: float = 15.0
    provider: str = "stub"
    product_url: str | None = None
    created_at: str


class GenerateScriptResponse(BaseModel):
    script: ScriptRecord


class ScriptGetResponse(BaseModel):
    script: ScriptRecord
