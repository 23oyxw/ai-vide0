# Agent 参考建议

> **已实现落地**：见 [docs/RAG.md](docs/RAG.md) 与 `orchestrator/rag/`  
> 修改本文件后，对话中 @ 本文件 或说「参考 AGENT_REFERENCE.md」。

---

## 项目背景与目标

IntelliSafe-RAG 情报底座 + AI 电商种草视频八层编排（L1–L8）。  
RAG 固定流水线：**Reader → 元数据 → 切分 → 索引 → 查询**，对接 `/rag/*`、`/report`、`/agent/crawler`、`/monitor`。

---

## 技术偏好

- LlamaIndex 模块化、可按需插拔；未安装 `requirements-rag.txt` 时走 **stub 关键词检索**
- 元数据提取默认关闭（成本控制）；热点文档可开 `use_extractors`
- 嵌入优先本地 `BAAI/bge-small-zh-v1.5`；Chroma 持久化
- 混合索引：Vector + Keyword + Summary → ComposableGraph（完整依赖时）

---

## 架构与模块说明

| 层 | 模块 | API |
|----|------|-----|
| L1 热点 | `readers.load_from_web` + auto-ingest | `/agent/crawler` |
| 流水线 | `pipeline.run_ingestion_pipeline` + Cache | `/rag/ingest` |
| 问答 | Vector / Graph QueryEngine | `/rag/query` |
| L6 质检 | 广告法 + PII 脱敏 | `/rag/check`, `/monitor` |
| L8 报表 | SummaryIndex | `/report` |

代码目录：`orchestrator/rag/` · 样例知识库：`data/knowledge/`

**Git 与开源依赖**：见 [docs/GIT_REPOS.md](docs/GIT_REPOS.md)（LlamaIndex / Chroma / FastAPI 仓库地址、私有仓结构对照、v1.0–v1.4 迭代）。

---

## 开发流程

```powershell
pip install -r requirements.txt
pip install -r requirements-rag.txt   # 可选
uvicorn orchestrator.main:app --reload --port 8765
curl -X POST http://127.0.0.1:8765/rag/ingest -H "Content-Type: application/json" -d "{\"source\":\"directory\"}"
```

Dashboard：**知识库** Tab → `/api/rag/*` 代理。

---

## 待办 / 已知问题

- [x] KnowledgeGraphIndex 竞品关系图谱（stub 三元组 + `/rag/kg/query`）
- [x] TreeIndex 对接 L8 报表（`l8_sync.py` + `/rag/sync/l8` + `/report?job_id=`）
- [x] Token 预算预跑（`/rag/estimate-cost`）
- [x] L2/L6 管线内自动注入 RAG 上下文
- [x] 完整 LlamaIndex KnowledgeGraphIndex / TreeIndex（`indexes.py` + `mode=kg|tree`）
- [x] L8 持久化指标（SQLite 本地 + Postgres 可选，`adapters/l8_store.py`）
- [x] 生产 L8 写入 pipeline（`upsert_daily_metrics` + `POST /modules/l8-analytics/metrics` + `/webhooks/analytics` + 管线 L8 自动写入）

---

## 策略原文（LlamaIndex 书本章节笔记）

完整笔记见 **[docs/LLAMAINDEX_STRATEGY.md](docs/LLAMAINDEX_STRATEGY.md)**（你补充的书本章节 + IntelliSafe 融合方案原文保留）。

