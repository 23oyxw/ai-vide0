from __future__ import annotations

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult
from orchestrator.pipeline_state import QA_PASS_THRESHOLD

DEFAULT_OPTIMIZATION_HINTS = [
    "提高前3秒 hook 强度 -> 反馈 L2 脚本模板",
    "L2: 缩短口播句长，提升完播率",
    "L3: 增加产品特写镜头占比",
    "L1: 低效 SKU 降权，优先高转化类目",
]


def _hints_from_qa(score: float, failed_checks: str) -> list[str]:
    hints: list[str] = []
    if score < QA_PASS_THRESHOLD:
        hints.append(
            f"L2: QA score {score:.2f} 低于阈值 {QA_PASS_THRESHOLD}，优先重写脚本 hook"
        )
    elif score < 0.85:
        hints.append(f"L2: QA score {score:.2f}，可加强前3秒钩子与口播节奏")

    if "duration_15s" in failed_checks:
        hints.append("L3: 分镜总时长偏离 15s，调整 segments 起止点")
    if "final_video_exists" in failed_checks:
        hints.append("L4: final.mp4 缺失，检查 video-factory 渲染日志")
    if "scene_count" in failed_checks:
        hints.append("L3: 镜头数不足，补全 hook/产品/CTA 结构")
    return hints


class DataLayer(BaseLayer):
    layer_id = "L8"
    name = "data"
    description = "Analytics - Postgres + ECharts; feeds optimization_hints back to L1/L2"

    async def run(self, ctx: LayerContext) -> LayerResult:
        try:
            qa_score = float(ctx.artifacts.get("qa_score", "0.85"))
        except ValueError:
            qa_score = 0.85

        failed_checks = ctx.artifacts.get("qa_checks_failed", "")
        hints = _hints_from_qa(qa_score, failed_checks)
        hints.extend(DEFAULT_OPTIMIZATION_HINTS)

        publish_target = ctx.artifacts.get("publish_target", "")
        if publish_target:
            hints.insert(
                0,
                f"L7: 发布目标 {publish_target}，video={ctx.artifacts.get('video_path', 'n/a')}",
            )

        metrics = {
            "job_id": ctx.job_id,
            "qa_score": qa_score,
            "publish_target": publish_target,
            "manifest_path": ctx.artifacts.get("manifest_path", ""),
            "video_path": ctx.artifacts.get("video_path", ""),
            "segment_count": ctx.artifacts.get("segment_count", ""),
            "pipeline_mode": ctx.artifacts.get("pipeline_mode", ""),
        }

        ctx.metadata["optimization_hints"] = hints
        ctx.metadata["metrics"] = metrics
        ctx.artifacts["metrics_recorded"] = ctx.job_id
        ctx.artifacts["optimization_hints"] = "|".join(hints[:6])
        ctx.artifacts["metrics_json"] = str(metrics)

        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=f"metrics recorded (qa={qa_score:.3f}); {len(hints)} optimization hints",
            artifacts={
                "metrics_recorded": ctx.job_id,
                "optimization_hints": "|".join(hints[:6]),
                "metrics_json": str(metrics),
            },
        )
