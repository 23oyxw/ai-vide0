from __future__ import annotations

import json
import logging
from typing import Any

from orchestrator.rag import settings as rag_settings
from orchestrator.rag.cost import estimate_ingest_cost
from orchestrator.rag.indexes import (
    LlamaIndexManager,
    get_llama_manager,
    get_stub_index,
)
from orchestrator.rag import knowledge_graph
from orchestrator.rag.l8_sync import build_l8_hierarchical_text, sync_l8_to_rag
from orchestrator.rag.metadata_ops import compliance_check
from orchestrator.rag.models import (
    KgGraphResponse,
    KgQueryRequest,
    KgQueryResponse,
    L8SyncRequest,
    RagCheckResponse,
    RagCostEstimateRequest,
    RagCostEstimateResponse,
    RagIngestRequest,
    RagIngestResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagStatusResponse,
    RagUserRequest,
    RagUserResponse,
    ReportRequest,
    ReportResponse,
)
from orchestrator.rag.pipeline import run_ingestion_pipeline
from orchestrator.rag.readers import (
    documents_from_texts,
    enrich_metadata,
    load_from_database,
    load_from_directory,
    load_from_web,
)

logger = logging.getLogger(__name__)


class RAGService:
    """Fixed pipeline: read → metadata → split → index → query (AGENT_REFERENCE)."""

    def _kg_stats(self) -> tuple[int, int]:
        stats = knowledge_graph.graph_stats()
        return stats["triplets"], stats["entities"]

    def status(self) -> RagStatusResponse:
        from orchestrator.adapters.l8_store import data_source_label

        stub = get_stub_index()
        mgr = get_llama_manager()
        built = bool(mgr._vector_engine) if LlamaIndexManager.available() else False
        triplets, entities = self._kg_stats()
        return RagStatusResponse(
            llama_index_installed=LlamaIndexManager.available(),
            chroma_path=str(rag_settings.CHROMA_DIR),
            knowledge_dir=str(rag_settings.KNOWLEDGE_DIR),
            stub_nodes=len(stub.nodes),
            llama_index_built=built,
            kg_triplets=triplets,
            kg_entities=entities,
            l8_data_source=data_source_label(),
            llama_tree_built=mgr.tree_built,
            llama_kg_built=mgr.kg_built,
        )

    def bootstrap(self) -> RagIngestResponse | None:
        """Startup: load knowledge dir if index empty."""
        stub = get_stub_index()
        if stub.nodes:
            return None
        if not rag_settings.KNOWLEDGE_DIR.exists():
            rag_settings.KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
            return None
        req = RagIngestRequest(source="directory", category="电商种草情报")
        result = self.ingest(req)
        logger.info("RAG bootstrap: %s", result.message)
        return result

    def _load_documents(self, req: RagIngestRequest) -> tuple[list[dict[str, Any]], str]:
        if req.source == "directory":
            path = req.directory or str(rag_settings.KNOWLEDGE_DIR)
            return load_from_directory(path), "file"
        if req.source == "web":
            return load_from_web(req.urls), "web"
        if req.source == "database":
            if req.database_uri and req.database_query:
                return load_from_database(req.database_uri, req.database_query), "database"
            return [], "database"
        if req.source == "l8":
            from orchestrator.adapters.l8_store import export_metrics_documents, init_local_store

            init_local_store()
            docs = export_metrics_documents()
            docs.append(
                {
                    "text": build_l8_hierarchical_text(),
                    "metadata": {"source_type": "l8_analytics", "layer": "L8"},
                }
            )
            return docs, "l8_analytics"
        return documents_from_texts(req.texts), "inline"

    def estimate_cost(self, req: RagCostEstimateRequest) -> RagCostEstimateResponse:
        ingest_req = RagIngestRequest(
            source=req.source,
            directory=req.directory,
            urls=req.urls,
            texts=req.texts,
            splitter=req.splitter,
            use_extractors=req.use_extractors,
            build_llama_index=req.build_llama_index,
        )
        documents, _ = self._load_documents(ingest_req)
        data = estimate_ingest_cost(
            documents,
            splitter=req.splitter,
            use_extractors=req.use_extractors,
            build_llama_index=req.build_llama_index,
        )
        return RagCostEstimateResponse(**data)

    def ingest(self, req: RagIngestRequest) -> RagIngestResponse:
        documents, source_type = self._load_documents(req)

        if req.source == "database" and not documents:
            return RagIngestResponse(
                documents=0,
                nodes=0,
                engine="none",
                message="database_uri and database_query required",
            )

        if not documents:
            return RagIngestResponse(
                documents=0,
                nodes=0,
                engine="none",
                message="no documents loaded — check paths/urls",
            )

        documents = enrich_metadata(
            documents, source_type=source_type, category=req.category
        )
        nodes = run_ingestion_pipeline(
            documents,
            source_type=source_type,
            category=req.category,
            splitter=req.splitter,
            use_extractors=req.use_extractors,
        )

        kg_added = 0
        for doc in documents:
            kg_added += knowledge_graph.ingest_text(
                doc.get("text", ""), doc.get("metadata")
            )

        stub = get_stub_index()
        stub.add_nodes(nodes)
        engine = "stub"

        if req.build_llama_index and LlamaIndexManager.available():
            try:
                get_llama_manager().build_from_nodes(nodes)
                engine = "llama_index+chroma"
            except Exception as exc:
                logger.exception("llama index build failed")
                engine = f"stub (llama build failed: {exc})"
        elif req.build_llama_index:
            engine = "stub (install requirements-rag.txt for full index)"

        return RagIngestResponse(
            documents=len(documents),
            nodes=len(nodes),
            engine=engine,
            message=f"ingested {len(documents)} docs → {len(nodes)} nodes · KG +{kg_added} triplets",
        )

    def query(self, req: RagQueryRequest) -> RagQueryResponse:
        mgr = get_llama_manager()
        if LlamaIndexManager.available() and mgr._vector_engine:
            try:
                if req.mode == "summary":
                    result = mgr.query_summary(req.question)
                elif req.mode == "graph":
                    result = mgr.query_graph(req.question)
                elif req.mode == "tree":
                    result = mgr.query_tree(req.question)
                elif req.mode == "kg":
                    result = mgr.query_kg(req.question)
                else:
                    result = mgr.query_vector(req.question)
                return RagQueryResponse(
                    response=result["response"],
                    engine=result["engine"],
                    sources=[],
                )
            except Exception as exc:
                logger.warning("llama query failed, fallback stub: %s", exc)

        if req.mode == "kg":
            triplets = knowledge_graph.query_entity(req.question)
            if triplets:
                lines = [f"{t['subject']} --{t['predicate']}--> {t['object']}" for t in triplets]
                return RagQueryResponse(
                    response="【stub KG】\n" + "\n".join(lines),
                    engine="stub_kg",
                    sources=triplets,
                )

        if req.mode == "tree":
            tree_text = build_l8_hierarchical_text()
            return RagQueryResponse(
                response=f"【stub Tree / L8】\n{tree_text[:1000]}",
                engine="stub_tree_l8",
                sources=[],
            )

        stub_result = get_stub_index().query(req.question)
        return RagQueryResponse(
            response=stub_result["response"],
            engine=stub_result["engine"],
            sources=stub_result.get("sources", []),
        )

    def query_kg(self, req: KgQueryRequest) -> KgQueryResponse:
        triplets = knowledge_graph.query_entity(req.entity)
        return KgQueryResponse(entity=req.entity, triplets=triplets, count=len(triplets))

    def get_kg_graph(self) -> KgGraphResponse:
        data = knowledge_graph.export_graph()
        return KgGraphResponse(
            triplets=data["triplets"],
            entities=data["entities"],
            count=data["count"],
        )

    def check(self, text: str) -> RagCheckResponse:
        data = compliance_check(text)
        return RagCheckResponse(
            passed=data["passed"],
            score=data["score"],
            prohibited_hits=data["prohibited_hits"],
            pii_hits=data["pii_hits"],
            message=data["message"],
            redacted_preview=data["redacted_preview"],
        )

    def set_user_prefs(self, req: RagUserRequest) -> RagUserResponse:
        rag_settings.RAG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        store: dict[str, Any] = {}
        if rag_settings.USER_PREFS_FILE.exists():
            try:
                store = json.loads(
                    rag_settings.USER_PREFS_FILE.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                store = {}
        store[req.user_id] = req.preferences
        rag_settings.USER_PREFS_FILE.write_text(
            json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return RagUserResponse(user_id=req.user_id, preferences=req.preferences)

    def get_user_prefs(self, user_id: str) -> RagUserResponse:
        if not rag_settings.USER_PREFS_FILE.exists():
            return RagUserResponse(user_id=user_id, preferences={})
        try:
            store = json.loads(
                rag_settings.USER_PREFS_FILE.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            store = {}
        return RagUserResponse(
            user_id=user_id, preferences=store.get(user_id, {})
        )

    def report(self, req: ReportRequest) -> ReportResponse:
        if req.job_id:
            sync_l8_to_rag(req.job_id)
            tree_text = build_l8_hierarchical_text(req.job_id)
            stub = get_stub_index()
            stub.add_nodes(
                [{"text": tree_text, "metadata": {"job_id": req.job_id, "layer": "L8"}}]
            )
            return ReportResponse(
                summary=f"【L8 Tree 报表 job={req.job_id}】\n{tree_text[:1200]}",
                engine="stub_tree_l8",
                hints=["已同步 L8 指标至 RAG 分层节点"],
            )

        mgr = get_llama_manager()
        if LlamaIndexManager.available() and mgr._summary_engine:
            try:
                result = mgr.query_summary(req.question)
                return ReportResponse(
                    summary=result["response"],
                    engine=result["engine"],
                    hints=["ComposableGraph SummaryIndex"],
                )
            except Exception as exc:
                logger.warning("summary report failed: %s", exc)

        stub = get_stub_index().summarize_all(req.question)
        return ReportResponse(
            summary=stub["response"],
            engine=stub["engine"],
            hints=[
                "传入 job_id 可生成 L8 分层 Tree 报表",
                "安装 requirements-rag.txt 启用 SummaryIndex",
            ],
        )

    def sync_l8(self, req: L8SyncRequest) -> dict[str, Any]:
        return sync_l8_to_rag(req.job_id)

    def ingest_crawl_text(self, text: str, url: str, title: str = "") -> int:
        documents = documents_from_texts(
            [text],
            metadata={"url": url, "title": title, "source_type": "web"},
        )
        nodes = run_ingestion_pipeline(
            documents, source_type="web", category="热点采集"
        )
        knowledge_graph.ingest_text(text, {"url": url, "title": title})
        return get_stub_index().add_nodes(nodes)


rag_service = RAGService()
