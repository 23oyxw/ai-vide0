from __future__ import annotations

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class SchedulerLayer(BaseLayer):
    layer_id = "L5"
    name = "scheduler"
    description = "Job scheduling - FastAPI orchestrator + OpenClaw Agent"

    async def run(self, ctx: LayerContext) -> LayerResult:
        ctx.artifacts["scheduled_job"] = ctx.job_id
        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=f"job {ctx.job_id} scheduled (stub)",
            artifacts={"scheduled_job": ctx.job_id},
        )
