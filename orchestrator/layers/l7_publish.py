from __future__ import annotations

from pathlib import Path

from orchestrator.adapters.ai_koubo import publish_video
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


def _resolve_video_path(artifacts: dict[str, str]) -> str:
    output_dir = artifacts.get("video_factory_output", "")
    if not output_dir:
        return artifacts.get("video_path", "")

    path = Path(output_dir)
    if path.is_dir():
        candidates = sorted(path.rglob("final.mp4"), reverse=True)
        if candidates:
            return str(candidates[0])
    elif path.suffix == ".mp4" and path.exists():
        return str(path)
    return artifacts.get("video_path", "")


class PublishLayer(BaseLayer):
    layer_id = "L7"
    name = "publish"
    description = "Publish - ai-koubo publish provider"

    async def run(self, ctx: LayerContext) -> LayerResult:
        script = ctx.artifacts.get("script", "")
        result = await publish_video(
            job_id=ctx.job_id,
            video_path=_resolve_video_path(ctx.artifacts),
            title=script[:40] if script else "",
            cover_path=ctx.artifacts.get("cover_path", ""),
        )
        ctx.artifacts.update(result.get("artifacts", {}))
        return LayerResult(
            layer_id=self.layer_id,
            status=result["status"],
            message=result["message"],
            artifacts=result.get("artifacts", {}),
        )
