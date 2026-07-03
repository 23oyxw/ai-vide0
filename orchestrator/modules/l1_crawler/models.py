from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    keyword: str | None = None
    vertical: str = "电商"
    product_url: str | None = None
    competitor_urls: list[str] = Field(default_factory=list)


class TrendingTopic(BaseModel):
    keyword: str
    heat: int
    vertical: str
    source: str = "curated"


class TopicRecord(BaseModel):
    id: str
    keyword: str
    vertical: str
    heat: int
    crawled_url: str | None = None
    title: str = ""
    description: str = ""
    category: str = ""
    created_at: str


class SearchResponse(BaseModel):
    topics: list[TrendingTopic]
    crawl: TopicRecord | None = None
    stored_count: int


class TopicsListResponse(BaseModel):
    topics: list[TopicRecord]
    total: int
