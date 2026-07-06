from __future__ import annotations

from typing import Any

from orchestrator.rag.splitters import SplitterKind

# 粗算：中文约 1.5 字符/token，英文约 4 字符/token
CHARS_PER_TOKEN_ZH = 1.5
CHARS_PER_TOKEN_EN = 4.0

# 元数据提取器大约额外 token（Summary + Keyword per chunk）
EXTRACTOR_TOKENS_PER_CHUNK = 120
DEFAULT_CHUNK_COUNT_RATIO = 3  # 文档数 * ratio ≈ chunk 数


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    zh = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other = len(text) - zh
    return int(zh / CHARS_PER_TOKEN_ZH + other / CHARS_PER_TOKEN_EN)


def estimate_ingest_cost(
    documents: list[dict[str, Any]],
    *,
    splitter: SplitterKind = "token",
    use_extractors: bool = False,
    build_llama_index: bool = False,
) -> dict[str, Any]:
    total_chars = sum(len(d.get("text", "")) for d in documents)
    base_tokens = estimate_tokens("".join(d.get("text", "") for d in documents))
    chunk_multiplier = {
        "token": 1.0,
        "sentence_window": 1.2,
        "hierarchical": 2.5,
        "code": 1.1,
    }.get(splitter, 1.0)
    est_chunks = max(1, int(len(documents) * DEFAULT_CHUNK_COUNT_RATIO * chunk_multiplier))
    embed_tokens = int(base_tokens * 0.9)
    extractor_tokens = est_chunks * EXTRACTOR_TOKENS_PER_CHUNK if use_extractors else 0
    index_tokens = embed_tokens if build_llama_index else 0
    total = embed_tokens + extractor_tokens + index_tokens
    return {
        "documents": len(documents),
        "total_chars": total_chars,
        "estimated_chunks": est_chunks,
        "embed_tokens": embed_tokens,
        "extractor_tokens": extractor_tokens,
        "index_tokens": index_tokens,
        "total_estimated_tokens": total,
        "use_extractors": use_extractors,
        "build_llama_index": build_llama_index,
        "recommendation": (
            "成本偏高，建议关闭 use_extractors 或缩小文档集"
            if total > 50_000
            else "在可控范围内，可继续 ingest"
        ),
    }
