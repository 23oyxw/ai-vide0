from __future__ import annotations

import json
from pathlib import Path

from orchestrator.layers.l6_qa import _qa_from_manifest
from orchestrator.adapters.content_safety import PROHIBITED_WORDS, RISKY_WORDS, check_content
from orchestrator.modules.common import module_dir, save_json, utc_now_iso
from orchestrator.modules.l6_qa.models import QACheckResult, RulesResponse, ValidateRequest, ValidateResponse
from orchestrator.config import settings
from orchestrator.pipeline_state import QA_PASS_THRESHOLD

RULES_FILE = module_dir("l6") / "ban_words.json"


def _ensure_rules_file() -> Path:
    if not RULES_FILE.exists():
        save_json(
            RULES_FILE,
            {
                "prohibited": PROHIBITED_WORDS,
                "risky": RISKY_WORDS,
                "updated_at": utc_now_iso(),
            },
        )
    return RULES_FILE


def get_rules() -> RulesResponse:
    path = _ensure_rules_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    return RulesResponse(
        prohibited_words=list(data.get("prohibited", PROHIBITED_WORDS)),
        risky_words=list(data.get("risky", RISKY_WORDS)),
        pass_threshold=QA_PASS_THRESHOLD,
        rules_file=str(path),
    )


def validate(req: ValidateRequest) -> ValidateResponse:
    checks: list[QACheckResult] = []
    safety_hits: list[str] = []
    score = 1.0

    if req.force_fail:
        return ValidateResponse(
            passed=False,
            score=QA_PASS_THRESHOLD - 0.1,
            checks=[QACheckResult(name="forced_fail", passed=False, message="demo forced fail")],
            message="QA forced fail",
        )

    if req.script_text:
        safety = check_content(req.script_text)
        safety_hits = safety.hits
        checks.append(
            QACheckResult(
                name="content_safety",
                passed=safety.passed,
                score=safety.score,
                message=safety.message,
            )
        )
        if not safety.passed:
            return ValidateResponse(
                passed=False,
                score=safety.score,
                checks=checks,
                safety_hits=safety_hits,
                message=safety.message,
            )
        score = min(score, safety.score)

    if req.manifest_path:
        manifest_score, passed_names, failed_names = _qa_from_manifest(
            req.manifest_path, req.output_dir
        )
        score = min(score, manifest_score)
        for name in passed_names:
            checks.append(QACheckResult(name=name, passed=True, score=1.0))
        for name in failed_names:
            checks.append(QACheckResult(name=name, passed=False, score=0.0))

    if req.video_path:
        exists = Path(req.video_path).exists()
        checks.append(
            QACheckResult(
                name="video_file_exists",
                passed=exists,
                message="video found" if exists else "video missing",
            )
        )
        if not exists:
            score -= 0.2

    passed = score >= QA_PASS_THRESHOLD
    if settings.pipeline_mode == 'mock' and score >= 0.5 and not req.force_fail:
        passed = True
    return ValidateResponse(
        passed=passed,
        score=round(score, 3),
        checks=checks,
        safety_hits=safety_hits,
        message="QA passed" if passed else f"QA failed score={score:.3f}",
    )
