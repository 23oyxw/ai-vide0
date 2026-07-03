from __future__ import annotations

from fastapi import APIRouter

from orchestrator.modules.l1_crawler.models import SearchRequest, SearchResponse, TopicsListResponse
from orchestrator.modules.l1_crawler import service
from orchestrator.schemas import ApiEnvelope, ok_envelope

router = APIRouter(prefix="/modules/l1-crawler", tags=["M1 热点检索"])

legacy_router = APIRouter(prefix="/agent", tags=["M1 热点检索 (legacy)"])


@router.post("/search", response_model=ApiEnvelope[SearchResponse])
async def post_search(req: SearchRequest) -> ApiEnvelope[SearchResponse]:
    data = await service.search_topics(req)
    return ok_envelope(data, layer="L1", job_id=data.crawl.id if data.crawl else None)


@router.get("/topics", response_model=ApiEnvelope[TopicsListResponse])
async def get_topics() -> ApiEnvelope[TopicsListResponse]:
    return ok_envelope(service.list_topics(), layer="L1")


@legacy_router.get("/crawler")
async def legacy_crawler_get(product_url: str | None = None) -> ApiEnvelope:
    return await _legacy_crawler_response(SearchRequest(product_url=product_url))


@legacy_router.post("/crawler")
async def legacy_crawler_post(req: SearchRequest) -> ApiEnvelope:
    return await _legacy_crawler_response(req)


async def _legacy_crawler_response(body: SearchRequest) -> ApiEnvelope:
    from orchestrator.schemas import CrawlerData, SelectionCard

    data = await service.search_topics(body)
    crawl = data.crawl
    url = crawl.crawled_url if crawl else (body.product_url or "https://example.com/product")
    title = crawl.title if crawl else "Demo Product"
    category = crawl.category if crawl else "unknown"
    return ok_envelope(
        CrawlerData(
            crawled_url=url,
            selection_card=SelectionCard(title=title or "Demo Product", category=category),
            competitor_count=len(body.competitor_urls),
            rag_candidates=[f"rag_{t.keyword}" for t in data.topics[:3]],
        ),
        layer="L1",
        job_id=crawl.id if crawl else None,
    )

