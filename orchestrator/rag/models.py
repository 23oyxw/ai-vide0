from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from orchestrator.rag.splitters import SplitterKind


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: Literal["vector", "summary", "graph", "tree", "kg", "auto"] = "auto"


class RagQueryResponse(BaseModel):
    response: str
    engine: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class RagIngestRequest(BaseModel):
    source: Literal["directory", "web", "database", "texts", "l8"] = "directory"
    directory: str | None = None
    urls: list[str] = Field(default_factory=list)
    database_uri: str | None = None
    database_query: str | None = None
    texts: list[str] = Field(default_factory=list)
    category: str = "电商种草情报"
    splitter: SplitterKind = "token"
    use_extractors: bool = False
    build_llama_index: bool = False


class RagIngestResponse(BaseModel):
    documents: int
    nodes: int
    engine: str
    message: str


class RagCheckRequest(BaseModel):
    text: str = Field(min_length=1)


class RagCheckResponse(BaseModel):
    passed: bool
    score: float
    prohibited_hits: list[str]
    pii_hits: list[dict[str, str]]
    message: str
    redacted_preview: str


class RagUserRequest(BaseModel):
    user_id: str = "default"
    preferences: dict[str, Any] = Field(default_factory=dict)


class RagUserResponse(BaseModel):
    user_id: str
    preferences: dict[str, Any]


class ReportRequest(BaseModel):
    question: str = Field(min_length=1)
    job_id: str | None = None


class ReportResponse(BaseModel):
    summary: str
    engine: str
    hints: list[str] = Field(default_factory=list)


class RagStatusResponse(BaseModel):
    llama_index_installed: bool
    chroma_path: str
    knowledge_dir: str
    stub_nodes: int
    llama_index_built: bool
    kg_triplets: int = 0
    kg_entities: int = 0
    l8_data_source: str = "demo"
    llama_tree_built: bool = False
    llama_kg_built: bool = False


class RagCostEstimateRequest(BaseModel):
    source: Literal["directory", "web", "database", "texts", "l8"] = "directory"
    directory: str | None = None
    urls: list[str] = Field(default_factory=list)
    texts: list[str] = Field(default_factory=list)
    splitter: SplitterKind = "token"
    use_extractors: bool = False
    build_llama_index: bool = False


class RagCostEstimateResponse(BaseModel):
    documents: int
    total_chars: int
    estimated_chunks: int
    embed_tokens: int
    extractor_tokens: int
    index_tokens: int
    total_estimated_tokens: int
    recommendation: str


class KgQueryRequest(BaseModel):
    entity: str = Field(min_length=1)


class KgQueryResponse(BaseModel):
    entity: str
    triplets: list[dict[str, str]]
    count: int


class KgGraphResponse(BaseModel):
    triplets: list[dict[str, str]]
    entities: list[str]
    count: int


class L8SyncRequest(BaseModel):
    job_id: str | None = None

