from __future__ import annotations

from pathlib import Path

from orchestrator.config import settings

KNOWLEDGE_DIR: Path = settings.rag_knowledge_dir
RAG_CACHE_DIR: Path = settings.rag_cache_dir
CHROMA_DIR: Path = settings.rag_chroma_dir
INGESTION_CACHE_FILE: Path = RAG_CACHE_DIR / "ingestion_cache.bin"
PERSIST_DIR: Path = RAG_CACHE_DIR / "index_storage"
STUB_DOCS_FILE: Path = RAG_CACHE_DIR / "stub_documents.json"
USER_PREFS_FILE: Path = RAG_CACHE_DIR / "user_preferences.json"

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 60
DEFAULT_CATEGORY = "电商种草情报"

EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
