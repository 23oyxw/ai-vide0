from __future__ import annotations

import logging
from typing import Any

from orchestrator.rag import settings as rag_settings
from orchestrator.rag.readers import enrich_metadata
from orchestrator.rag.splitters import SplitterKind, configure_global_settings, split_documents

logger = logging.getLogger(__name__)


def run_ingestion_pipeline(
    documents: list[dict[str, Any]],
    *,
    source_type: str = "file",
    category: str = rag_settings.DEFAULT_CATEGORY,
    splitter: SplitterKind = "token",
    use_extractors: bool = False,
) -> list[dict[str, Any]]:
    """Module 4.9 — read → split → optional metadata extractors → nodes."""
    rag_settings.RAG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    configure_global_settings()

    docs = enrich_metadata(documents, source_type=source_type, category=category)

    if use_extractors:
        nodes = _pipeline_with_extractors(docs)
    else:
        nodes = split_documents(docs, kind=splitter)

    return nodes


def _pipeline_with_extractors(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        from llama_index.core import Document
        from llama_index.core.ingestion import IngestionCache, IngestionPipeline
        from llama_index.core.node_parser import TokenTextSplitter
        from llama_index.core.extractors import KeywordExtractor, SummaryExtractor

        llama_docs = [
            Document(text=d["text"], metadata=d.get("metadata", {})) for d in documents
        ]
        cache = None
        cache_path = rag_settings.INGESTION_CACHE_FILE
        if cache_path.exists():
            try:
                cache = IngestionCache.from_persist_path(str(cache_path))
            except Exception:
                cache = None

        pipeline = IngestionPipeline(
            transformations=[
                TokenTextSplitter(
                    chunk_size=rag_settings.DEFAULT_CHUNK_SIZE,
                    chunk_overlap=rag_settings.DEFAULT_CHUNK_OVERLAP,
                ),
                SummaryExtractor(summaries=["self"]),
                KeywordExtractor(keywords=5),
            ],
            cache=cache,
        )
        nodes = pipeline.run(documents=llama_docs)
        if pipeline.cache:
            pipeline.cache.persist(str(cache_path))
        return [{"text": n.get_content(), "metadata": dict(n.metadata)} for n in nodes]
    except ImportError:
        logger.info("LlamaIndex extractors unavailable — using token splitter only")
        return split_documents(documents)
    except Exception as exc:
        logger.warning("ingestion pipeline failed: %s", exc)
        return split_documents(documents)
