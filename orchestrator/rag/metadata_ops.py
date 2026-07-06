from __future__ import annotations

import re
from typing import Any

from orchestrator.adapters.content_safety import check_content

# Module 4.8 — lightweight PII patterns (NERPI substitute when extractors unavailable)
PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("phone", re.compile(r"1[3-9]\d{9}")),
    ("email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    (
        "id_card",
        re.compile(r"\b\d{17}[\dXx]\b"),
    ),
]


def scan_pii(text: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for label, pattern in PII_PATTERNS:
        for match in pattern.finditer(text):
            hits.append({"type": label, "value": match.group()})
    return hits


def redact_pii(text: str) -> tuple[str, list[dict[str, str]]]:
    redacted = text
    hits = scan_pii(text)
    for hit in hits:
        redacted = redacted.replace(hit["value"], f"[{hit['type'].upper()}_REDACTED]")
    return redacted, hits


def compliance_check(text: str) -> dict[str, Any]:
    """Combine ad-law keywords + PII for /rag/check and /monitor."""
    safety = check_content(text)
    pii_hits = scan_pii(text)
    passed = safety.passed and len(pii_hits) == 0
    return {
        "passed": passed,
        "score": safety.score if safety.passed else min(safety.score, 0.5),
        "prohibited_hits": safety.hits,
        "pii_hits": pii_hits,
        "message": safety.message
        if safety.passed
        else safety.message,
        "redacted_preview": redact_pii(text)[0][:500] if pii_hits else text[:500],
    }
