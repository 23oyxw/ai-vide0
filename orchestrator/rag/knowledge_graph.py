from __future__ import annotations

import json
import re
from typing import Any

from orchestrator.rag import settings as rag_settings

KG_FILE = rag_settings.RAG_CACHE_DIR / "knowledge_graph.json"

# 竞品 / 达人 / 商品 简易三元组模式（stub KG，LlamaIndex KG 可后续替换）
_TRIPLET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("competitor", re.compile(r"([^\s，,]{2,12})(?:对标|竞品|vs|VS)([^\s，,]{2,12})")),
    ("influencer_product", re.compile(r"([^\s，,]{2,8}达人?)(?:带货|推荐|测评)([^\s，,]{2,20})")),
    ("brand_product", re.compile(r"([A-Za-z\u4e00-\u9fff]{2,10}品牌?)(?:推出|发布|上新)([^\s，,]{2,20})")),
]


def _load_graph() -> dict[str, Any]:
    rag_settings.RAG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if KG_FILE.exists():
        try:
            data = json.loads(KG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"triplets": [], "entities": {}}


def _save_graph(data: dict[str, Any]) -> None:
    KG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_triplets(text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, str]]:
    triplets: list[dict[str, str]] = []
    meta = metadata or {}
    for rel, pattern in _TRIPLET_PATTERNS:
        for match in pattern.finditer(text):
            triplets.append(
                {
                    "subject": match.group(1),
                    "predicate": rel,
                    "object": match.group(2),
                    "source": str(meta.get("url") or meta.get("file_name") or "inline"),
                }
            )
    return triplets


def ingest_text(text: str, metadata: dict[str, Any] | None = None) -> int:
    graph = _load_graph()
    new_triplets = extract_triplets(text, metadata)
    existing = {(t["subject"], t["predicate"], t["object"]) for t in graph["triplets"]}
    added = 0
    for t in new_triplets:
        key = (t["subject"], t["predicate"], t["object"])
        if key not in existing:
            graph["triplets"].append(t)
            existing.add(key)
            added += 1
            for entity in (t["subject"], t["object"]):
                graph["entities"].setdefault(entity, []).append(t)
    if added:
        _save_graph(graph)
    return added


def query_entity(entity: str) -> list[dict[str, str]]:
    graph = _load_graph()
    entity = entity.strip()
    if not entity:
        return []
    direct = graph["entities"].get(entity, [])
    if direct:
        return direct
    return [
        t
        for t in graph["triplets"]
        if entity in t["subject"] or entity in t["object"]
    ]


def graph_stats() -> dict[str, int]:
    graph = _load_graph()
    return {
        "triplets": len(graph.get("triplets", [])),
        "entities": len(graph.get("entities", {})),
    }


def export_graph() -> dict[str, Any]:
    graph = _load_graph()
    triplets = graph.get("triplets", [])
    entities = list(graph.get("entities", {}).keys())
    return {
        "triplets": triplets,
        "entities": entities,
        "count": len(triplets),
    }
