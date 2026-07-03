from __future__ import annotations

from orchestrator.adapters.storyboard import load_storyboard
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class StoryboardLayer(BaseLayer):
    layer_id = "L3"
    name = "storyboard"
    description = "Storyboard YAML - video-factory demos"

    async def run(self, ctx: LayerContext) -> LayerResult:
        result = load_storyboard(ctx.demo_name)
        artifacts: dict[str, str] = {}

        if result["status"] == "ok":
            ctx.demo_name = result["demo_name"]
            artifacts = {
                "storyboard_yaml": result["yaml_path"],
                "storyboard_title": result["title"],
                "storyboard_type": result["type"],
                "storyboard_segments": result["segments"],
                "segment_count": result["segment_count"],
                "duration_target_sec": result["duration_target_sec"],
                "demo_name": result["demo_name"],
            }
            if result.get("width"):
                artifacts["storyboard_width"] = result["width"]
            if result.get("height"):
                artifacts["storyboard_height"] = result["height"]
            if result.get("fps"):
                artifacts["storyboard_fps"] = result["fps"]
        elif result["status"] == "skipped":
            yaml_name = f"{ctx.demo_name}.yaml"
            artifacts["storyboard_yaml"] = result.get("yaml_path", yaml_name)
            artifacts["demo_name"] = ctx.demo_name
        else:
            ctx.errors.append(result["message"])

        ctx.artifacts.update(artifacts)
        status = "error" if result["status"] == "error" else "ok"
        return LayerResult(
            layer_id=self.layer_id,
            status=status,
            message=result["message"],
            artifacts=artifacts,
        )
