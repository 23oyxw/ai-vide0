from __future__ import annotations

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class ContentLayer(BaseLayer):
    layer_id = "L2"
    name = "content"
    description = "Script generation - DeepSeek via ai-koubo / Cline"

    async def run(self, ctx: LayerContext) -> LayerResult:
        script = "[stub] product seeding script"
        ctx.artifacts["script"] = script
        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message="stub script generated",
            artifacts={"script": script},
        )
