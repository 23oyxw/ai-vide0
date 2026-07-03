from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LayerContext(BaseModel):
    """Pipeline execution context passed between layers."""

    job_id: str
    product_url: str | None = None
    demo_name: str = "post_production_15s_zhongcao"
    c4d_project: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class LayerResult(BaseModel):
    layer_id: str
    status: str  # ok | skipped | error
    message: str = ""
    artifacts: dict[str, str] = Field(default_factory=dict)


class BaseLayer(ABC):
    layer_id: str
    name: str
    description: str

    @abstractmethod
    async def run(self, ctx: LayerContext) -> LayerResult:
        ...
