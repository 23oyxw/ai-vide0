from __future__ import annotations

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class StoryboardLayer(BaseLayer):
    layer_id = "L3"
    name = "storyboard"
    description = "Storyboard YAML - video-factory demos"

    async def run(self, ctx: LayerContext) -> LayerResult:
        yaml_name = f"{ctx.demo_name}.yaml"
        ctx.artifacts["storyboard_yaml"] = yaml_name
        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=f"storyboard ref: {yaml_name}",
            artifacts={"storyboard_yaml": yaml_name},
        )
