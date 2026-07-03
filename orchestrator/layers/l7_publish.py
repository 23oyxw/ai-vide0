from __future__ import annotations

from orchestrator.adapters.ai_koubo import publish_stub
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class PublishLayer(BaseLayer):
    layer_id = "L7"
    name = "publish"
    description = "Publish - ai-koubo publish provider"

    async def run(self, ctx: LayerContext) -> LayerResult:
        result = publish_stub(ctx.job_id)
        ctx.artifacts.update(result.get("artifacts", {}))
        return LayerResult(
            layer_id=self.layer_id,
            status=result["status"],
            message=result["message"],
            artifacts=result.get("artifacts", {}),
        )
