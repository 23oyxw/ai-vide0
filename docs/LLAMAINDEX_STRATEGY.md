# LlamaIndex 可复用标准化落地策略

> 来源：AGENT_REFERENCE 用户笔记 · 对应实现 `orchestrator/rag/` · [RAG.md](./RAG.md)

## 固定流水线

环境依赖 → 多源读取 → 文档拆节点 → 元数据优化 → 向量索引 → 问答查询 → 日志调试

## 一、统一前置依赖

```bash
pip install -r requirements-rag.txt
```

## 二、多数据源 Reader（`orchestrator/rag/readers.py`）

| 场景 | Reader | 函数 |
|------|--------|------|
| 网页热点 L1 | SimpleWebPageReader | `load_from_web` |
| 业务库 L8 | DatabaseReader | `load_from_database` |
| 商家知识库 | SimpleDirectoryReader | `load_from_directory` |

## 三、节点切分三档（`splitters.py`）

- **token** — 通用文案/报表（512/60）
- **sentence_window** — 知识库问答首选
- **hierarchical** — 长文档多级摘要（2048/512/128）
- **code** — 运维/开发文档

## 四、元数据 & 成本控制

- 批量 `source_type` / `collect_time` / `category`
- 提取器默认关闭；`use_extractors=true` 启用 Summary + Keyword
- IngestionCache 避免重复计算

## 五、索引选型 & API 映射

| API | 索引 | 层 |
|-----|------|-----|
| `/rag/query` | Vector + ComposableGraph | RAG |
| `/rag/ingest` | 流水线 | L1 |
| `/rag/check` | 关键词 + PII | L6 |
| `/report` | SummaryIndex | L8 |
| `/agent/crawler` | 爬虫 + auto-ingest | L1 |

## 六、混合索引优先级

1. Vector + Keyword（日常问答）
2. TreeIndex（分层报表，待 L8 数据）
3. KnowledgeGraphIndex（竞品关联，待实现）
4. ComposableGraph 统一收口

## 七、实验反思

1. 无缓存时重复 ingest 开销大 → 已实现 IngestionCache 路径
2. 全量元数据提取 token 成本高 → 默认关闭 extractors
3. 单一向量索引全局汇总差 → SummaryIndex + `/report`
4. 无 PII 脱敏有风险 → `/rag/check` + L6 monitor
5. 无持久化启动慢 → Chroma + `data/rag_cache/`

## 八、待扩展（AGENT_REFERENCE 待办）

- KnowledgeGraphIndex 竞品关系
- TreeIndex 对接 Postgres 报表
- MockLLM token 预算预跑
- L2/L6 管线自动 RAG 上下文注入

---

*完整书本章节原文若需恢复，请从本地备份粘贴至本文件末尾。*
