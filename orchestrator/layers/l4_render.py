from __future__ import annotations

from orchestrator.adapters.c4d import render_project
from orchestrator.adapters.c4d_scene2 import render_scene2_stub
from orchestrator.adapters.video_factory import run_demo
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class RenderLayer(BaseLayer):
    layer_id = "L4"
    name = "render"
    description = "Render - video-factory + C4D scene2 stub + OpenClaw video_generate"

    async def run(self, ctx: LayerContext) -> LayerResult:
        artifacts: dict[str, str] = {}
        messages: list[str] = []

        demo_name = ctx.artifacts.get("demo_name") or ctx.demo_name
        ctx.demo_name = demo_name

        vf_result = run_demo(demo_name)
        if vf_result["status"] == "ok":
            artifacts["video_factory_output"] = vf_result.get("output_dir", "")
            if vf_result.get("manifest_path"):
                artifacts["manifest_path"] = vf_result["manifest_path"]
            if vf_result.get("final_video"):
                artifacts["video_path"] = vf_result["final_video"]
            if vf_result.get("pipeline_mode"):
                artifacts["pipeline_mode"] = vf_result["pipeline_mode"]
            messages.append(vf_result["message"])
        elif vf_result["status"] == "skipped":
            messages.append(vf_result["message"])
        else:
            ctx.errors.append(vf_result["message"])
            messages.append(f"video-factory error: {vf_result['message']}")

        manifest_path = artifacts.get("manifest_path", "")
        output_dir = artifacts.get("video_factory_output", "")
        if manifest_path and ctx.metadata.get("c4d_scene2", True):
            c4d_s2 = render_scene2_stub(manifest_path, output_dir)
            if c4d_s2["status"] == "ok":
                artifacts["c4d_scene2_output"] = c4d_s2.get("output", "")
                messages.append(c4d_s2["message"])
            elif c4d_s2["status"] == "skipped":
                messages.append(f"c4d S2: {c4d_s2['message']}")
            else:
                messages.append(f"c4d S2 error: {c4d_s2['message']}")

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
