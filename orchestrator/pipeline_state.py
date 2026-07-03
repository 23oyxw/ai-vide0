from __future__ import annotations

from enum import Enum

LAYER_ORDER: list[str] = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
LAYER_INDEX: dict[str, int] = {lid: idx for idx, lid in enumerate(LAYER_ORDER)}

QA_RETRY_FROM = "L2"
QA_PASS_THRESHOLD = 0.7


class PipelineState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    L4_RENDER = "l4_render"
    QA_FAILED = "qa_failed"
    PUBLISHED = "published"
    ANALYZED = "analyzed"
    ERROR = "error"