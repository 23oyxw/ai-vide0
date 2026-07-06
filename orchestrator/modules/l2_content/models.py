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


class OptimizePromptsRequest(BaseModel):
    product_url: str = ""
    topic: str = ""
    script: str = ""
    product_title: str = ""
    category: str = ""
    pain_points: list[str] = Field(default_factory=list)
    platform: str = "抖音/小红书"


class OptimizePromptsResponse(BaseModel):
    optimized_topic: str
    optimized_script: str
    hook_suggestions: list[str]
    rag_snippets: list[str]
    next_steps: list[str]
    provider: str = "rag-template"


class GenerateProductImageRequest(BaseModel):
    product_url: str = ""
    product_title: str = ""
    category: str = ""
    reference_image_url: str = ""  # 参考产品图 URL → 图生图，保证一致性
    image_types: list[str] = Field(
        default_factory=lambda: ["白底主图", "场景氛围图", "卖点特写图"]
    )


class ProductImageVariant(BaseModel):
    type: str
    url: str
    prompt: str
    width: int = 512
    height: int = 512


class GenerateProductImageResponse(BaseModel):
    images: list[ProductImageVariant]
    provider: str = "stub"
    product_title: str
    category: str
