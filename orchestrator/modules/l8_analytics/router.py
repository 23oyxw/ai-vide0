from __future__ import annotations

from fastapi import APIRouter, Query

from orchestrator.modules.l8_analytics import service
from orchestrator.modules.l8_analytics.models import (
    AnalysisResponse,
    ClickResponse,
    ConversionResponse,
    DashboardResponse,
    OrderResponse,
)
from orchestrator.schemas import (
    ApiEnvelope,
    DataAnalysisData,
    DataAnalysisRequest,
    DataClickData,
    DataConversionData,
    DataOrderData,
    ok_envelope,
)

router = APIRouter(prefix="/modules/l8-analytics", tags=["M8 数据运营"])
legacy_router = APIRouter(prefix="/data", tags=["M8 数据运营 (legacy)"])


@router.get("/dashboard", response_model=ApiEnvelope[DashboardResponse])
async def get_dashboard(job_id: str | None = Query(default=None)) -> ApiEnvelope[DashboardResponse]:
    return ok_envelope(service.get_dashboard(job_id), layer="L8", job_id=job_id)


@router.get("/click", response_model=ApiEnvelope[ClickResponse])
async def get_click(job_id: str | None = Query(default=None)) -> ApiEnvelope[ClickResponse]:
    return ok_envelope(service.get_click(job_id), layer="L8", job_id=job_id)


@router.get("/conversion", response_model=ApiEnvelope[ConversionResponse])
async def get_conversion(job_id: str | None = Query(default=None)) -> ApiEnvelope[ConversionResponse]:
    return ok_envelope(service.get_conversion(job_id), layer="L8", job_id=job_id)


@router.get("/order", response_model=ApiEnvelope[OrderResponse])
async def get_order(job_id: str | None = Query(default=None)) -> ApiEnvelope[OrderResponse]:
    return ok_envelope(service.get_order(job_id), layer="L8", job_id=job_id)


@router.get("/analysis", response_model=ApiEnvelope[AnalysisResponse])
async def get_analysis(job_id: str | None = Query(default=None)) -> ApiEnvelope[AnalysisResponse]:
    return ok_envelope(service.get_analysis(job_id), layer="L8", job_id=job_id)


@legacy_router.get("/click")
async def legacy_click(job_id: str | None = Query(default=None)) -> ApiEnvelope[DataClickData]:
    data = service.get_click(job_id)
    return ok_envelope(
        DataClickData(clicks=data.clicks, unique_clicks=data.unique_clicks, ctr=data.ctr, records=data.records),
        layer="L8",
        job_id=job_id,
    )


@legacy_router.get("/conversion")
async def legacy_conversion(job_id: str | None = Query(default=None)) -> ApiEnvelope[DataConversionData]:
    data = service.get_conversion(job_id)
    return ok_envelope(
        DataConversionData(conversions=data.conversions, conversion_rate=data.conversion_rate, records=data.records),
        layer="L8",
        job_id=job_id,
    )


@legacy_router.get("/order")
async def legacy_order(job_id: str | None = Query(default=None)) -> ApiEnvelope[DataOrderData]:
    data = service.get_order(job_id)
    return ok_envelope(
        DataOrderData(orders=data.orders, gmv=data.gmv, records=data.records),
        layer="L8",
        job_id=job_id,
    )


@legacy_router.get("/analysis")
async def legacy_analysis(job_id: str | None = Query(default=None)) -> ApiEnvelope[DataAnalysisData]:
    data = service.get_analysis(job_id)
    return ok_envelope(
        DataAnalysisData(summary=data.summary, optimization_hints=data.optimization_hints, feedback_targets=data.feedback_targets),
        layer="L8",
        job_id=job_id,
    )


@legacy_router.post("/click")
async def legacy_click_post(body: dict) -> ApiEnvelope[DataClickData]:
    job_id = body.get("job_id")
    return await legacy_click(job_id)


@legacy_router.post("/conversion")
async def legacy_conversion_post(body: dict) -> ApiEnvelope[DataConversionData]:
    return await legacy_conversion(body.get("job_id"))


@legacy_router.post("/order")
async def legacy_order_post(body: dict) -> ApiEnvelope[DataOrderData]:
    return await legacy_order(body.get("job_id"))


@legacy_router.post("/analysis")
async def legacy_analysis_post(req: DataAnalysisRequest) -> ApiEnvelope[DataAnalysisData]:
    return await legacy_analysis(req.job_id)
