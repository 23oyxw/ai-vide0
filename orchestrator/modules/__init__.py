"""Eight standalone L1-L8 modules with FastAPI routers."""

from __future__ import annotations

from fastapi import APIRouter

from orchestrator.modules.l1_crawler import legacy_router as l1_legacy, router as l1_router
from orchestrator.modules.l2_content import router as l2_router
from orchestrator.modules.l3_storyboard import router as l3_router
from orchestrator.modules.l4_render import router as l4_router
from orchestrator.modules.l5_scheduler import router as l5_router
from orchestrator.modules.l6_qa import legacy_router as l6_legacy, router as l6_router
from orchestrator.modules.l7_publish import router as l7_router
from orchestrator.modules.l8_analytics import legacy_router as l8_legacy, router as l8_router
from orchestrator.rag.router import report_router, router as rag_router

MODULE_ROUTERS: list[APIRouter] = [
    l1_router,
    l1_legacy,
    l2_router,
    l3_router,
    l4_router,
    l5_router,
    l6_router,
    l6_legacy,
    l7_router,
    l8_router,
    l8_legacy,
    rag_router,
    report_router,
]

MODULE_REGISTRY: dict[str, str] = {
    "M1": "l1-crawler",
    "M2": "l2-content",
    "M3": "l3-storyboard",
    "M4": "l4-render",
    "M5": "l5-scheduler",
    "M6": "l6-qa",
    "M7": "l7-publish",
    "M8": "l8-analytics",
    "RAG": "intellisafe-rag",
}


def mount_modules(app) -> None:
    for router in MODULE_ROUTERS:
        app.include_router(router)
