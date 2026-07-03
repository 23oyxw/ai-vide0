from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from orchestrator.adapters.content_safety import PROHIBITED_WORDS, RISKY_WORDS, check_content
from orchestrator.layers.l6_qa import _qa_from_manifest
from orchestrator.pipeline_state import QA_PASS_THRESHOLD


class ValidateRequest(BaseModel):
    manifest_path: str = ""
    output_dir: str = ""
    script_text: str = ""
    video_path: str = ""
    force_fail: bool = False


class QACheckResult(BaseModel):
    name: str
    passed: bool
    score: float | None = None
    message: str = ""


class ValidateResponse(BaseModel):
    passed: bool
    score: float
    checks: list[QACheckResult]
    safety_hits: list[str] = Field(default_factory=list)
    message: str


class RulesResponse(BaseModel):
    prohibited_words: list[str]
    risky_words: list[str]
    pass_threshold: float
    rules_file: str
