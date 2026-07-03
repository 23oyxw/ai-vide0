from __future__ import annotations

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult
from orchestrator.pipeline_state import QA_PASS_THRESHOLD


class QALayer(BaseLayer):
    layer_id = "L6"
    name = "qa"
    description = "Quality check - RAG stub + /monitor; failure triggers retry_from L2"

    async def run(self, ctx: LayerContext) -> LayerResult:
        if ctx.metadata.get("force_qa_fail"):
            score = QA_PASS_THRESHOLD - 0.1
            ctx.artifacts["qa_score"] = str(score)
            ctx.errors.append(f"QA forced fail (demo): score={score}")
            return LayerResult(
                layer_id=self.layer_id,
                status="error",
                message=f"QA failed (forced): score={score}",
                artifacts={"qa_score": str(score)},
            )

        score = 0.85
        ctx.artifacts["qa_score"] = str(score)
        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=f"QA score: {score} (stub)",
            artifacts={"qa_score": str(score)},
        )
