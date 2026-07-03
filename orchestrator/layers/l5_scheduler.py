from __future__ import annotations

from orchestrator.job_store import job_store
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult
from orchestrator.pipeline_state import PipelineState


class SchedulerLayer(BaseLayer):
    layer_id = "L5"
    name = "scheduler"
    description = "Job scheduling - FastAPI orchestrator + OpenClaw Agent"

    async def run(self, ctx: LayerContext) -> LayerResult:
        state = {
            "status": PipelineState.RUNNING.value,
            "demo_name": ctx.demo_name,
            "product_url": ctx.product_url or "",
            "manifest_path": ctx.artifacts.get("manifest_path", ""),
            "video_path": ctx.artifacts.get("video_path", ""),
            "storyboard_yaml": ctx.artifacts.get("storyboard_yaml", ""),
            "segment_count": ctx.artifacts.get("segment_count", ""),
            "pipeline_mode": ctx.artifacts.get("pipeline_mode", ""),
            "layer_progress": "L5",
        }
        job_path = job_store.save(ctx.job_id, state)
        ctx.artifacts["scheduled_job"] = ctx.job_id
        ctx.artifacts["job_store_path"] = str(job_path)
        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=f"job {ctx.job_id} persisted to {job_path.name}",
            artifacts={
                "scheduled_job": ctx.job_id,
                "job_store_path": str(job_path),
            },
        )
