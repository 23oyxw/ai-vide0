from __future__ import annotations

import json
import re
from pathlib import Path

from orchestrator.adapters.content_safety import check_content
from orchestrator.adapters.video_factory import read_manifest
from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult
from orchestrator.pipeline_state import QA_PASS_THRESHOLD


def _qa_from_manifest(manifest_path: str, output_dir: str) -> tuple[float, list[str], list[str]]:
    """Return (score, checks_passed, checks_failed)."""
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    score = 1.0

    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        checks_failed.append("manifest_exists")
        return 0.0, checks_passed, checks_failed

    checks_passed.append("manifest_exists")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    run_dir = manifest_file.parent

    final_name = manifest.get("final_video", "final.mp4")
    final_path = run_dir / str(final_name)
    if final_path.exists():
        checks_passed.append("final_video_exists")
    else:
        checks_failed.append("final_video_exists")
        score -= 0.4

    scenes = manifest.get("scenes") or []
    total_duration = 0.0
    for scene in scenes:
        if isinstance(scene, dict):
            try:
                total_duration += float(scene.get("duration") or 0)
            except (TypeError, ValueError):
                pass

    target = 15.0
    if 13.0 <= total_duration <= 17.0:
        checks_passed.append("duration_15s")
    else:
        checks_failed.append("duration_15s")
        score -= 0.2

    if len(scenes) >= 3:
        checks_passed.append("scene_count")
    else:
        checks_failed.append("scene_count")
        score -= 0.15

    assets_dir = run_dir / "assets"
    if assets_dir.exists() and any(assets_dir.iterdir()):
        checks_passed.append("assets_present")
    else:
        checks_failed.append("assets_present")
        score -= 0.1

    if not output_dir or Path(output_dir).exists():
        checks_passed.append("output_dir_exists")
    else:
        checks_failed.append("output_dir_exists")
        score -= 0.15

    return max(0.0, min(1.0, score)), checks_passed, checks_failed


class QALayer(BaseLayer):
    layer_id = "L6"
    name = "qa"
    description = "Quality check - RAG stub + /monitor; failure triggers retry_from L2"

    async def run(self, ctx: LayerContext) -> LayerResult:
        manifest_path = ctx.artifacts.get("manifest_path", "")
        output_dir = ctx.artifacts.get("video_factory_output", "")
        script_text = str(ctx.metadata.get("script", ""))

        safety = check_content(script_text) if script_text else None
        if safety and not safety.passed:
            ctx.artifacts["qa_safety_score"] = str(round(safety.score, 3))
            ctx.artifacts["qa_safety_hits"] = ",".join(safety.hits)
            ctx.errors.append(safety.message)
            return LayerResult(
                layer_id=self.layer_id,
                status="error",
                message=f"QA content safety failed: {safety.message}",
                artifacts={
                    "qa_score": str(round(safety.score, 3)),
                    "qa_checks_failed": "safety_check",
                    "qa_safety_hits": ",".join(safety.hits),
                },
            )
        elif safety:
            ctx.artifacts["qa_safety_score"] = str(round(safety.score, 3))
            if safety.hits:
                ctx.artifacts["qa_safety_hits"] = ",".join(safety.hits)

        if ctx.metadata.get("force_qa_fail"):
            score = QA_PASS_THRESHOLD - 0.1
            ctx.artifacts["qa_score"] = str(score)
            ctx.artifacts["qa_checks_failed"] = "forced_fail"
            ctx.errors.append(f"QA forced fail (demo): score={score}")
            return LayerResult(
                layer_id=self.layer_id,
                status="error",
                message=f"QA failed (forced): score={score}",
                artifacts={
                    "qa_score": str(score),
                    "qa_checks_failed": "forced_fail",
                },
            )

        if manifest_path:
            score, passed, failed = _qa_from_manifest(manifest_path, output_dir)
        else:
            score = 0.75
            passed = ["stub_no_manifest"]
            failed = ["manifest_path"]

        ctx.artifacts["qa_score"] = str(round(score, 3))
        ctx.artifacts["qa_checks_passed"] = ",".join(passed)
        if failed:
            ctx.artifacts["qa_checks_failed"] = ",".join(failed)

        if score < QA_PASS_THRESHOLD:
            ctx.errors.append(
                f"QA score {score:.3f} below threshold {QA_PASS_THRESHOLD}"
            )
            return LayerResult(
                layer_id=self.layer_id,
                status="error",
                message=f"QA failed: score={score:.3f}, failed={','.join(failed)}",
                artifacts={
                    "qa_score": str(round(score, 3)),
                    "qa_checks_passed": ",".join(passed),
                    "qa_checks_failed": ",".join(failed),
                },
            )

        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=f"QA score: {score:.3f} (passed={len(passed)}, failed={len(failed)})",
            artifacts={
                "qa_score": str(round(score, 3)),
                "qa_checks_passed": ",".join(passed),
                "qa_checks_failed": ",".join(failed) if failed else "",
            },
        )
