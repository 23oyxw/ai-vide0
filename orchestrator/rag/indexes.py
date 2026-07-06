from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from orchestrator.rag import settings as rag_settings

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> set[str]:
    parts = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", text.lower())
    return set(parts)


class StubIndex:
    """Keyword + overlap fallback when LlamaIndex / Chroma not installed."""

    def __init__(self) -> None:
        rag_settings.RAG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.nodes: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if rag_settings.STUB_DOCS_FILE.exists():
            try:
                data = json.loads(rag_settings.STUB_DOCS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def persist(self) -> None:
        rag_settings.STUB_DOCS_FILE.write_text(
            json.dumps(self.nodes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_nodes(self, nodes: list[dict[str, Any]]) -> int:
        self.nodes.extend(nodes)
        self.persist()
        return len(nodes)

    def query(self, question: str, top_k: int = 5) -> dict[str, Any]:
        q_tokens = _tokenize(question)
        if not self.nodes:
            return {
                "response": "知识库为空。请先 POST /rag/ingest 导入文档，或安装 requirements-rag.txt。",
                "sources": [],
                "engine": "stub",
            }
        scored: list[tuple[float, dict[str, Any]]] = []
        for node in self.nodes:
            text = node.get("text", "")
            t_tokens = _tokenize(text)
            if not t_tokens:
                continue
            overlap = len(q_tokens & t_tokens)
            score = overlap / math.sqrt(len(t_tokens))
            if overlap:
                scored.append((score, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [n for _, n in scored[:top_k]]
        if not top:
            top = self.nodes[:top_k]
        snippet = top[0].get("text", "")[:400] if top else ""
        return {
            "response": f"【stub 检索】与「{question}」最相关片段：\n{snippet}",
            "sources": [
                {
                    "text": n.get("text", "")[:200],
                    "metadata": n.get("metadata", {}),
                }
                for n in top
            ],
            "engine": "stub",
        }

    def keyword_lookup(self, term: str, top_k: int = 5) -> list[dict[str, Any]]:
        hits = [n for n in self.nodes if term in n.get("text", "")]
        return hits[:top_k]

    def summarize_all(self, question: str) -> dict[str, Any]:
        combined = "\n".join(n.get("text", "")[:300] for n in self.nodes[:20])
        return {
            "response": f"【stub 摘要】共 {len(self.nodes)} 节点。问题：{question}\n预览：{combined[:800]}",
            "engine": "stub",
        }


class LlamaIndexManager:
    """Vector + Summary + Keyword + Tree + KnowledgeGraph + ComposableGraph."""

    def __init__(self) -> None:
        self._vector_engine = None
        self._summary_engine = None
        self._tree_engine = None
        self._kg_engine = None
        self._graph_engine = None
        self._nodes: list[Any] = []
        self.tree_built = False
        self.kg_built = False

    @staticmethod
    def available() -> bool:
        try:
            import llama_index.core  # noqa: F401

            return True
        except ImportError:
            return False

    def build_from_nodes(self, nodes: list[dict[str, Any]]) -> int:
        from llama_index.core import Document, Settings, SummaryIndex, VectorStoreIndex
        from llama_index.core import KeywordTableIndex, ComposableGraph, TreeIndex
        from llama_index.core.storage.storage_context import StorageContext

        rag_settings.RAG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        rag_settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            Settings.embed_model = HuggingFaceEmbedding(
                model_name=rag_settings.EMBED_MODEL
            )
        except Exception as exc:
            logger.warning("HF embed model unavailable (%s) — using default embed", exc)

        llama_docs = [
            Document(text=n["text"], metadata=n.get("metadata", {})) for n in nodes
        ]

        vector_store = None
        storage_context = None
        try:
            import chromadb
            from llama_index.vector_stores.chroma import ChromaVectorStore

            db = chromadb.PersistentClient(path=str(rag_settings.CHROMA_DIR))
            collection = db.get_or_create_collection("ecommerce_rag")
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
        except Exception as exc:
            logger.warning("Chroma unavailable (%s) — in-memory vector index", exc)

        vector_index = VectorStoreIndex.from_documents(
            llama_docs, storage_context=storage_context
        )
        keyword_index = KeywordTableIndex.from_documents(llama_docs)
        summary_index = SummaryIndex.from_documents(llama_docs)

        sub_indices = [vector_index, keyword_index, summary_index]
        summaries = [
            "向量索引：商家知识库语义问答",
            "关键词索引：类目/术语精准检索",
            "摘要索引：大盘情报汇总",
        ]

        self.tree_built = False
        self._tree_engine = None
        try:
            tree_index = TreeIndex.from_documents(llama_docs)
            self._tree_engine = tree_index.as_query_engine()
            sub_indices.append(tree_index)
            summaries.append("树索引：分层架构与 L8 报表查询")
            self.tree_built = True
        except Exception as exc:
            logger.warning("TreeIndex build skipped: %s", exc)

        self.kg_built = False
        self._kg_engine = None
        try:
            from llama_index.core import KnowledgeGraphIndex

            kg_index = KnowledgeGraphIndex.from_documents(
                llama_docs,
                max_triplets_per_chunk=8,
                include_embeddings=True,
            )
            self._kg_engine = kg_index.as_query_engine(include_text=True)
            sub_indices.append(kg_index)
            summaries.append("知识图谱：竞品/达人/商品关联")
            self.kg_built = True
        except Exception as exc:
            logger.warning("KnowledgeGraphIndex build skipped: %s", exc)

        graph = ComposableGraph.from_indices(
            SummaryIndex,
            sub_indices,
            index_summaries=summaries,
        )

        self._vector_engine = vector_index.as_query_engine(similarity_top_k=5)
        self._summary_engine = summary_index.as_query_engine()
        self._graph_engine = graph.as_query_engine()
        self._nodes = llama_docs

        if storage_context:
            storage_context.persist(persist_dir=str(rag_settings.PERSIST_DIR))

        return len(nodes)

    def query_vector(self, question: str) -> dict[str, Any]:
        if not self._vector_engine:
            raise RuntimeError("index not built")
        resp = self._vector_engine.query(question)
        return {"response": str(resp), "engine": "vector"}

    def query_summary(self, question: str) -> dict[str, Any]:
        if not self._summary_engine:
            raise RuntimeError("index not built")
        resp = self._summary_engine.query(question)
        return {"response": str(resp), "engine": "summary"}

    def query_tree(self, question: str) -> dict[str, Any]:
        if not self._tree_engine:
            raise RuntimeError("tree index not built")
        resp = self._tree_engine.query(question)
        return {"response": str(resp), "engine": "tree"}

    def query_kg(self, question: str) -> dict[str, Any]:
        if not self._kg_engine:
            raise RuntimeError("knowledge graph not built")
        resp = self._kg_engine.query(question)
        return {"response": str(resp), "engine": "knowledge_graph"}

    def query_graph(self, question: str) -> dict[str, Any]:
        if not self._graph_engine:
            raise RuntimeError("index not built")
        resp = self._graph_engine.query(question)
        return {"response": str(resp), "engine": "composable_graph"}


_stub_index = StubIndex()
_llama_manager: LlamaIndexManager | None = None


def get_stub_index() -> StubIndex:
    return _stub_index


def get_llama_manager() -> LlamaIndexManager:
    global _llama_manager
    if _llama_manager is None:
        _llama_manager = LlamaIndexManager()
    return _llama_manager
