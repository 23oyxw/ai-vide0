from __future__ import annotations

from orchestrator.adapters.c4d import render_project
from orchestrator.adapters.video_factory import run_demo
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class RenderLayer(BaseLayer):
    layer_id = "L4"
    name = "render"
    description = "渲染 — video-factory + C4D MCP + OpenClaw video_generate"

    async def run(self, ctx: LayerContext) -> LayerResult:
        artifacts: dict[str, str] = {}
        messages: list[str] = []

        vf_result = run_demo(ctx.demo_name)
        if vf_result["status"] == "ok":
            artifacts["video_factory_output"] = vf_result.get("output_dir", "")
            messages.append(vf_result["message"])
        elif vf_result["status"] == "skipped":
            messages.append(vf_result["message"])
        else:
            ctx.errors.append(vf_result["message"])
            messages.append(f"video-factory error: {vf_result['message']}")

        if ctx.c4d_project:
            c4d_result = render_project(ctx.c4d_project)
            if c4d_result["status"] == "ok":
                artifacts["c4d_output"] = c4d_result.get("output", "")
                messages.append(c4d_result["message"])
            else:
                messages.append(f"c4d: {c4d_result['message']}")

        ctx.artifacts.update(artifacts)
        status = "error" if ctx.errors else "ok"
        return LayerResult(
            layer_id=self.layer_id,
            status=status,
            message="; ".join(messages) or "render stub",
            artifacts=artifacts,
        )
