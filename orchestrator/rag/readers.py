from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

DocDict = dict[str, Any]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def enrich_metadata(documents: list[DocDict], *, source_type: str, category: str) -> list[DocDict]:
    """Module 4 — batch attach source / time / category tags."""
    for doc in documents:
        meta = doc.setdefault("metadata", {})
        meta.setdefault("source_type", source_type)
        meta.setdefault("collect_time", _now())
        meta.setdefault("category", category)
    return documents


def load_from_directory(input_dir: str) -> list[DocDict]:
    """Module 2.3 — local PDF/Word/TXT via LlamaIndex or plain-text fallback."""
    try:
        from llama_index.core import SimpleDirectoryReader

        reader = SimpleDirectoryReader(input_dir=input_dir, recursive=True)
        raw = reader.load_data()
        return [{"text": d.text, "metadata": dict(d.metadata)} for d in raw]
    except ImportError:
        return _fallback_directory(input_dir)
    except Exception as exc:
        logger.warning("directory reader failed: %s", exc)
        return _fallback_directory(input_dir)


def _fallback_directory(input_dir: str) -> list[DocDict]:
    from pathlib import Path

    docs: list[DocDict] = []
    root = Path(input_dir)
    if not root.exists():
        return docs
    for path in root.rglob("*"):
        if path.suffix.lower() in {".txt", ".md", ".json"} and path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            docs.append(
                {
                    "text": text,
                    "metadata": {"file_name": path.name, "file_path": str(path)},
                }
            )
    return docs


def load_from_web(urls: list[str]) -> list[DocDict]:
    """Module 2.1 — web page reader."""
    if not urls:
        return []
    try:
        from llama_index.readers.web import SimpleWebPageReader

        raw = SimpleWebPageReader(html_to_text=True).load_data(urls)
        return [{"text": d.text, "metadata": dict(d.metadata)} for d in raw]
    except ImportError:
        return _fallback_web(urls)
    except Exception as exc:
        logger.warning("web reader failed: %s", exc)
        return _fallback_web(urls)


def _fallback_web(urls: list[str]) -> list[DocDict]:
    import httpx

    docs: list[DocDict] = []
    for url in urls:
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.get(url)
                text = re.sub(r"<[^>]+>", " ", resp.text)[:8000]
                docs.append({"text": text, "metadata": {"url": url}})
        except Exception as exc:
            docs.append({"text": f"[fetch failed] {url}: {exc}", "metadata": {"url": url}})
    return docs


def load_from_database(uri: str, query: str) -> list[DocDict]:
    """Module 2.2 — SQL business data."""
    try:
        from llama_index.readers.database import DatabaseReader

        reader = DatabaseReader(uri=uri)
        raw = reader.load_data(query=query)
        return [{"text": d.text, "metadata": dict(d.metadata)} for d in raw]
    except ImportError:
        return []
    except Exception as exc:
        logger.warning("database reader failed: %s", exc)
        return []


def documents_from_texts(texts: list[str], metadata: dict[str, Any] | None = None) -> list[DocDict]:
    base = metadata or {}
    return [{"text": t, "metadata": dict(base)} for t in texts if t.strip()]
