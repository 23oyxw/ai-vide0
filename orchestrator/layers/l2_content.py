from __future__ import annotations

from orchestrator.adapters.ai_koubo import generate_script
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class ContentLayer(BaseLayer):
    layer_id = "L2"
    name = "content"
    description = "Script generation - DeepSeek via ai-koubo / Cline"

    async def run(self, ctx: LayerContext) -> LayerResult:
        raw_text = str(ctx.metadata.get("topic") or ctx.metadata.get("script") or "")
        result = await generate_script(
            product_url=ctx.product_url,
            raw_text=raw_text,
            style="种草短视频",
        )
        ctx.artifacts.update(result.get("artifacts", {}))
        return LayerResult(
            layer_id=self.layer_id,
            status=result["status"],
            message=result["message"],
            artifacts=result.get("artifacts", {}),
        )
