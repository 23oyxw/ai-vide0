from __future__ import annotations

from orchestrator.rag.models import RagQueryRequest
from orchestrator.rag.service import rag_service


def fetch_rag_context(question: str, *, max_chars: int = 800) -> str:
    """Retrieve top RAG snippets for L2 script / L6 QA injection."""
    if not question.strip():
        return ""
    result = rag_service.query(RagQueryRequest(question=question.strip(), mode="auto"))
    parts: list[str] = []
    for src in result.sources[:3]:
        text = str(src.get("text", "")).strip()
        if text:
            parts.append(text)
    if not parts and result.response:
        parts.append(result.response[:max_chars])
    combined = "\n---\n".join(parts)
    return combined[:max_chars]
