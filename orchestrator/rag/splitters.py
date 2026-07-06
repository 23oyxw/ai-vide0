from __future__ import annotations

from typing import Any, Literal

SplitterKind = Literal["token", "sentence_window", "code", "hierarchical"]

NodeDict = dict[str, Any]


def split_documents(
    documents: list[dict[str, Any]],
    kind: SplitterKind = "token",
    *,
    chunk_size: int = 512,
    chunk_overlap: int = 60,
) -> list[NodeDict]:
    """Module 3 — pick splitter strategy and return node dicts."""
    try:
        from llama_index.core import Document
        from llama_index.core.node_parser import (
            CodeSplitter,
            HierarchicalNodeParser,
            SentenceWindowNodeParser,
            TokenTextSplitter,
        )

        llama_docs = [Document(text=d["text"], metadata=d.get("metadata", {})) for d in documents]
        if kind == "sentence_window":
            parser = SentenceWindowNodeParser.from_defaults(window_size=2)
        elif kind == "code":
            parser = CodeSplitter.from_defaults(
                language="python", chunk_lines=6, chunk_lines_overlap=2
            )
        elif kind == "hierarchical":
            parser = HierarchicalNodeParser(
                chunk_sizes=[2048, 512, 128], chunk_overlap=30
            )
        else:
            parser = TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separator=" ",
                backup_separators=["。", "！", "？", "\n"],
            )
        nodes = parser.get_nodes_from_documents(llama_docs)
        return [
            {"text": n.get_content(), "metadata": dict(n.metadata)}
            for n in nodes
        ]
    except ImportError:
        return _fallback_split(documents, chunk_size, chunk_overlap)


def _fallback_split(
    documents: list[dict[str, Any]], chunk_size: int, chunk_overlap: int
) -> list[NodeDict]:
    nodes: list[NodeDict] = []
    for doc in documents:
        text = doc.get("text", "")
        meta = doc.get("metadata", {})
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            nodes.append({"text": text[start:end], "metadata": dict(meta)})
            if end >= len(text):
                break
            start = max(start + 1, end - chunk_overlap)
    return nodes


def configure_global_settings(
    chunk_size: int = 512, chunk_overlap: int = 60
) -> None:
    """Module 5 — lock global LlamaIndex Settings."""
    try:
        from llama_index.core import Settings
        from llama_index.core.node_parser import TokenTextSplitter

        Settings.text_splitter = TokenTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
    except ImportError:
        return
