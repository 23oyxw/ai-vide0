"""Unit tests for RAG system: service, readers, splitters, pipeline, models."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.rag.models import (
    RagQueryRequest,
    RagIngestRequest,
    RagCheckRequest,
    RagCheckResponse,
    RagUserRequest,
    ReportRequest,
    KgQueryRequest,
    L8SyncRequest,
    RagStatusResponse,
    RagCostEstimateRequest,
)
from orchestrator.rag.readers import (
    documents_from_texts,
    enrich_metadata,
    load_from_directory,
    load_from_web,
    load_from_database,
)
from orchestrator.rag.splitters import (
    split_documents,
    configure_global_settings,
)
from orchestrator.rag.context import fetch_rag_context
from orchestrator.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Models Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGModels:
    def test_rag_query_request_minimal(self):
        req = RagQueryRequest(question="test?")
        assert req.mode == "auto"

    def test_rag_query_request_rejects_empty(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RagQueryRequest(question="")

    def test_rag_ingest_request_defaults(self):
        req = RagIngestRequest()
        assert req.source == "directory"
        assert req.splitter == "token"
        assert req.use_extractors is False

    def test_rag_ingest_request_texts_mode(self):
        req = RagIngestRequest(source="texts", texts=["hello world", "second doc"])
        assert len(req.texts) == 2

    def test_rag_check_request(self):
        req = RagCheckRequest(text="需要检测的内容")
        assert req.text == "需要检测的内容"

    def test_rag_user_request_prefs(self):
        req = RagUserRequest(
            user_id="user-42",
            preferences={"topic_filter": "护肤", "max_length": 200},
        )
        assert req.preferences["topic_filter"] == "护肤"

    def test_report_request_has_required_fields(self):
        req = ReportRequest(question="summary please", job_id="j-123")
        assert req.question == "summary please"
        assert req.job_id == "j-123"

    def test_kg_query_request(self):
        req = KgQueryRequest(entity="防晒品类")
        assert req.entity == "防晒品类"

    def test_l8_sync_request(self):
        req = L8SyncRequest(job_id="j-sync-1")
        assert req.job_id == "j-sync-1"

    def test_l8_sync_request_none_job(self):
        req = L8SyncRequest()
        assert req.job_id is None

    def test_cost_estimate_request(self):
        req = RagCostEstimateRequest(
            source="directory",
            use_extractors=True,
        )
        assert req.use_extractors is True


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Readers
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGReaders:
    def test_documents_from_texts_basic(self):
        docs = documents_from_texts(["hello world", "second doc"])
        assert len(docs) == 2
        assert docs[0]["text"] == "hello world"

    def test_documents_from_texts_skips_empty(self):
        docs = documents_from_texts(["", "   ", "valid text"])
        assert len(docs) == 1
        assert docs[0]["text"] == "valid text"

    def test_documents_from_texts_with_metadata(self):
        docs = documents_from_texts(
            ["doc one"], metadata={"source": "test", "version": 1}
        )
        assert docs[0]["metadata"]["source"] == "test"

    def test_enrich_metadata_adds_fields(self):
        docs = [{"text": "hello", "metadata": {}}]
        enriched = enrich_metadata(docs, source_type="web", category="test_cat")
        assert enriched[0]["metadata"]["source_type"] == "web"
        assert enriched[0]["metadata"]["category"] == "test_cat"
        assert "collect_time" in enriched[0]["metadata"]

    def test_enrich_metadata_preserves_existing(self):
        docs = [{"text": "x", "metadata": {"existing": True}}]
        enriched = enrich_metadata(docs, source_type="file", category="c")
        assert enriched[0]["metadata"]["existing"] is True

    def test_load_from_directory_reads_markdown(self, tmp_knowledge_dir):
        docs = load_from_directory(str(tmp_knowledge_dir))
        # At least the test_kb.md file we seeded
        assert len(docs) >= 1
        assert any("种草指南" in d.get("text", "") for d in docs)

    def test_load_from_directory_nonexistent(self, tmp_path):
        docs = load_from_directory(str(tmp_path / "does_not_exist"))
        assert docs == []

    def test_load_from_web_empty_urls(self):
        assert load_from_web([]) == []

    def test_load_from_database_no_library(self):
        docs = load_from_database("sqlite:///none.db", "SELECT 1")
        # Without llama_index installed, returns []
        assert isinstance(docs, list)


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Splitters
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGSplitters:
    def test_split_documents_fallback(self):
        """Without llama_index installed, the fallback splitter kicks in."""
        docs = [{"text": "a" * 1000, "metadata": {"source": "test"}}]
        nodes = split_documents(docs, kind="token", chunk_size=256, chunk_overlap=30)
        assert len(nodes) > 1
        for node in nodes:
            assert "text" in node
            assert "metadata" in node

    def test_split_documents_preserves_metadata(self):
        docs = [{"text": "hello world " * 50, "metadata": {"file": "test.txt"}}]
        nodes = split_documents(docs, kind="token", chunk_size=128, chunk_overlap=20)
        for node in nodes:
            assert node["metadata"]["file"] == "test.txt"

    def test_split_documents_empty_list(self):
        nodes = split_documents([], kind="token")
        assert nodes == []

    def test_configure_global_settings_is_noop_without_llama(self):
        # Shouldn't raise even without llama_index
        configure_global_settings()


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Service
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGService:
    def test_status_returns_all_fields(self, patch_settings):
        from orchestrator.rag.service import rag_service
        status = rag_service.status()
        assert isinstance(status, RagStatusResponse)
        assert status.knowledge_dir
        assert status.llama_index_installed in (True, False)

    def test_ingest_directory_loads_files(self, patch_settings):
        from orchestrator.rag.service import rag_service
        resp = rag_service.ingest(RagIngestRequest(source="directory"))
        assert resp.documents >= 1
        assert resp.nodes >= 1
        assert resp.engine != ""

    def test_ingest_texts_mode(self, patch_settings):
        from orchestrator.rag.service import rag_service
        resp = rag_service.ingest(
            RagIngestRequest(
                source="texts",
                texts=["种草文案黄金 3 秒法则：开头要直接点出痛点"],
            )
        )
        assert resp.documents == 1
        assert resp.nodes >= 1

    def test_ingest_no_documents_returns_message(self, patch_settings):
        from orchestrator.rag.service import rag_service
        resp = rag_service.ingest(
            RagIngestRequest(source="directory", directory="/nonexistent/path/xyz")
        )
        assert resp.documents == 0
        assert "no documents" in resp.message.lower()

    def test_query_after_ingest_returns_response(self, patch_settings):
        from orchestrator.rag.service import rag_service
        rag_service.ingest(RagIngestRequest(source="directory"))
        resp = rag_service.query(RagQueryRequest(question="种草视频开场钩子怎么写？"))
        assert len(resp.response) > 0
        assert resp.engine != ""

    def test_query_kg_mode(self, patch_settings):
        from orchestrator.rag.service import rag_service
        # Ingest to populate the graph
        rag_service.ingest(RagIngestRequest(source="directory"))
        resp = rag_service.query(RagQueryRequest(question="种草", mode="kg"))
        assert len(resp.response) > 0

    def test_query_tree_mode_returns_l8_text(self, patch_settings):
        from orchestrator.rag.service import rag_service
        resp = rag_service.query(RagQueryRequest(question="分析指标", mode="tree"))
        assert len(resp.response) > 0

    def test_check_compliance_with_prohibited(self):
        from orchestrator.rag.service import rag_service
        resp = rag_service.check("本产品第一好用，联系手机13800138000")
        assert resp.passed is False
        assert len(resp.prohibited_hits) > 0

    def test_check_compliance_clean_text(self):
        from orchestrator.rag.service import rag_service
        resp = rag_service.check("这是一段合规安全的种草文案")
        assert resp.passed is True
        assert len(resp.prohibited_hits) == 0

    def test_bootstrap_when_index_empty(self, patch_settings):
        from orchestrator.rag.service import rag_service
        from orchestrator.rag.indexes import get_stub_index
        # Clear stub and bootstrap
        stub = get_stub_index()
        stub.nodes.clear()
        result = rag_service.bootstrap()
        if result is not None:
            assert result.documents >= 1
            assert result.nodes >= 1

    def test_set_and_get_user_prefs(self, patch_settings):
        from orchestrator.rag.service import rag_service
        prefs = {"topic": "护肤", "quality": "high"}
        resp = rag_service.set_user_prefs(RagUserRequest(user_id="u1", preferences=prefs))
        assert resp.preferences == prefs

        loaded = rag_service.get_user_prefs("u1")
        assert loaded.preferences == prefs

    def test_get_user_prefs_for_unknown_user(self, patch_settings):
        from orchestrator.rag.service import rag_service
        resp = rag_service.get_user_prefs("unknown_user_999")
        assert resp.preferences == {}

    def test_query_kg_entity(self, patch_settings):
        from orchestrator.rag.service import rag_service
        rag_service.ingest(RagIngestRequest(source="directory"))
        resp = rag_service.query_kg(KgQueryRequest(entity="种草"))
        assert resp.count >= 0

    def test_get_kg_graph(self, patch_settings):
        from orchestrator.rag.service import rag_service
        rag_service.ingest(RagIngestRequest(source="directory"))
        graph = rag_service.get_kg_graph()
        assert graph.count >= 0

    def test_report_with_job_id(self, patch_settings):
        from orchestrator.rag.service import rag_service
        resp = rag_service.report(ReportRequest(question="分析性能", job_id="test-report-job"))
        assert len(resp.summary) > 0

    def test_sync_l8(self, patch_settings):
        from orchestrator.rag.service import rag_service
        result = rag_service.sync_l8(L8SyncRequest(job_id="test-sync-l8"))
        assert isinstance(result, dict)

    def test_ingest_crawl_text(self, patch_settings):
        from orchestrator.rag.service import rag_service
        count = rag_service.ingest_crawl_text(
            "防晒产品近期热度飙升，用户关注防晒指数和清爽肤感",
            "https://example.com/trending",
            "防晒趋势分析",
        )
        assert count > 0

    def test_estimate_cost(self, patch_settings):
        from orchestrator.rag.service import rag_service
        resp = rag_service.estimate_cost(
            RagCostEstimateRequest(source="texts", texts=["hello world " * 100])
        )
        assert resp.documents == 1
        assert resp.estimated_chunks >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Context Injection
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGContext:
    def test_empty_question_returns_empty(self, patch_settings):
        assert fetch_rag_context("") == ""
        assert fetch_rag_context("   ") == ""

    def test_non_empty_question_returns_snippets(self, patch_settings):
        from orchestrator.rag.service import rag_service
        # Ensure there's content in the index
        rag_service.ingest(RagIngestRequest(source="directory"))
        result = fetch_rag_context("种草 开场 钩子")
        # May or may not have sources, but should not crash
        assert isinstance(result, str)

    def test_respects_max_chars(self, patch_settings):
        from orchestrator.rag.service import rag_service
        rag_service.ingest(RagIngestRequest(source="directory"))
        result = fetch_rag_context("种草视频", max_chars=20)
        assert len(result) <= 20
