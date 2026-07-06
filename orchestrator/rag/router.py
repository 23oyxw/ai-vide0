from __future__ import annotations

from fastapi import APIRouter, Query

from orchestrator.rag.models import (
    KgGraphResponse,
    KgQueryRequest,
    KgQueryResponse,
    L8SyncRequest,
    RagCheckRequest,
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
from orchestrator.rag.service import rag_service
from orchestrator.schemas import ApiEnvelope, ok_envelope

router = APIRouter(prefix="/rag", tags=["IntelliSafe-RAG"])
report_router = APIRouter(tags=["IntelliSafe-RAG 报表"])


@router.get("/status", response_model=ApiEnvelope[RagStatusResponse])
async def rag_status() -> ApiEnvelope[RagStatusResponse]:
    return ok_envelope(rag_service.status(), layer="RAG")


@router.post("/query", response_model=ApiEnvelope[RagQueryResponse])
async def rag_query(req: RagQueryRequest) -> ApiEnvelope[RagQueryResponse]:
    return ok_envelope(rag_service.query(req), layer="RAG")


@router.post("/ingest", response_model=ApiEnvelope[RagIngestResponse])
async def rag_ingest(req: RagIngestRequest) -> ApiEnvelope[RagIngestResponse]:
    return ok_envelope(rag_service.ingest(req), layer="RAG")


@router.post("/estimate-cost", response_model=ApiEnvelope[RagCostEstimateResponse])
async def rag_estimate_cost(
    req: RagCostEstimateRequest,
) -> ApiEnvelope[RagCostEstimateResponse]:
    return ok_envelope(rag_service.estimate_cost(req), layer="RAG")


@router.post("/kg/query", response_model=ApiEnvelope[KgQueryResponse])
async def rag_kg_query(req: KgQueryRequest) -> ApiEnvelope[KgQueryResponse]:
    return ok_envelope(rag_service.query_kg(req), layer="RAG")


@router.get("/kg/graph", response_model=ApiEnvelope[KgGraphResponse])
async def rag_kg_graph() -> ApiEnvelope[KgGraphResponse]:
    return ok_envelope(rag_service.get_kg_graph(), layer="RAG")


@router.post("/sync/l8", response_model=ApiEnvelope[dict])
async def rag_sync_l8(req: L8SyncRequest) -> ApiEnvelope[dict]:
    return ok_envelope(
        rag_service.sync_l8(req), layer="L8", job_id=req.job_id
    )


@router.post("/check", response_model=ApiEnvelope[RagCheckResponse])
async def rag_check(req: RagCheckRequest) -> ApiEnvelope[RagCheckResponse]:
    return ok_envelope(rag_service.check(req.text), layer="RAG")


@router.post("/user", response_model=ApiEnvelope[RagUserResponse])
async def rag_user_post(req: RagUserRequest) -> ApiEnvelope[RagUserResponse]:
    return ok_envelope(rag_service.set_user_prefs(req), layer="RAG")


@router.get("/user", response_model=ApiEnvelope[RagUserResponse])
async def rag_user_get(
    user_id: str = Query(default="default"),
) -> ApiEnvelope[RagUserResponse]:
    return ok_envelope(rag_service.get_user_prefs(user_id), layer="RAG")


@report_router.post("/report", response_model=ApiEnvelope[ReportResponse])
async def report_post(req: ReportRequest) -> ApiEnvelope[ReportResponse]:
    return ok_envelope(rag_service.report(req), layer="L8")


@report_router.get("/report", response_model=ApiEnvelope[ReportResponse])
async def report_get(
    question: str = Query(default="总结近期美妆品类爆款种草套路"),
    job_id: str | None = Query(default=None),
) -> ApiEnvelope[ReportResponse]:
    return ok_envelope(
        rag_service.report(ReportRequest(question=question, job_id=job_id)),
        layer="L8",
        job_id=job_id,
    )
