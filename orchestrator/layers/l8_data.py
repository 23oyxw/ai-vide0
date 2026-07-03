from __future__ import annotations

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult

DEFAULT_OPTIMIZATION_HINTS = [
    "提高前3秒 hook 强度 -> 反馈 L2 脚本模板",
    "L2: 缩短口播句长，提升完播率",
    "L3: 增加产品特写镜头占比",
    "L1: 低效 SKU 降权，优先高转化类目",
]


class DataLayer(BaseLayer):
    layer_id = "L8"
    name = "data"
    description = "Analytics - Postgres + ECharts; feeds optimization_hints back to L1/L2"

    async def run(self, ctx: LayerContext) -> LayerResult:
        hints = list(DEFAULT_OPTIMIZATION_HINTS)
        ctx.metadata["optimization_hints"] = hints
        ctx.artifacts["metrics_recorded"] = ctx.job_id
        ctx.artifacts["optimization_hints"] = "|".join(hints)
        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message="metrics stub recorded; optimization_hints for L1/L2 closed loop",
            artifacts={
                "metrics_recorded": ctx.job_id,
                "optimization_hints": "|".join(hints),
            },
        )
