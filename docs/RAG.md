# IntelliSafe-RAG 架构说明

> 实现依据：[AGENT_REFERENCE.md](../AGENT_REFERENCE.md)  
> 对应 MASTER_PLAN §8 IntelliSafe RAG + 八层 L1/L6/L8

## 固定流水线

```
Reader（web / database / directory）
  → 元数据 enrichment（source / time / category）
  → NodeParser（token / sentence_window / hierarchical）
  → [可选] IngestionPipeline + Cache
  → Vector / Keyword / Summary / ComposableGraph
  → QueryEngine
```

## 目录结构

```
orchestrator/rag/
  readers.py      # 多数据源 Reader
  splitters.py    # 三档节点切分
  metadata_ops.py # 元数据 + PII/合规检测
  pipeline.py     # IngestionPipeline + 缓存
  indexes.py      # Stub / LlamaIndex + Chroma
  service.py      # 统一服务入口
  router.py       # FastAPI 路由
data/knowledge/   # 默认本地知识库
data/rag_cache/   # stub 文档 + ingestion cache
data/chroma_db/   # Chroma 持久化（可选）
```

## API 映射（四大接口）

| 接口 | 索引策略 | 层 |
|------|----------|-----|
| `POST /rag/query` | Vector + ComposableGraph | RAG / L2 L6 注入 |
| `POST /rag/ingest` | 流水线预处理 | L1 热点入库 |
| `POST /rag/check` | 关键词 + PII 脱敏 | L6 /monitor |
| `GET/POST /report` | SummaryIndex 汇总 | L8 报表 |
| `GET/POST /agent/crawler` | 爬虫后可 auto-ingest | L1 |

## 安装

```powershell
# 基础 orchestrator（无 RAG 重依赖，使用 stub 检索）
pip install -r requirements.txt

# 完整 LlamaIndex + Chroma + 本地嵌入
pip install -r requirements-rag.txt
```

## 快速验证

```powershell
curl -X POST http://127.0.0.1:8765/rag/ingest -H "Content-Type: application/json" -d "{\"source\":\"directory\"}"
curl -X POST http://127.0.0.1:8765/rag/query -H "Content-Type: application/json" -d "{\"question\":\"种草视频开场钩子怎么写？\"}"
curl -X POST http://127.0.0.1:8765/rag/estimate-cost -H "Content-Type: application/json" -d "{\"source\":\"directory\"}"
curl -X POST http://127.0.0.1:8765/rag/check -H "Content-Type: application/json" -d "{\"text\":\"本产品第一最好100%有效\"}"
curl "http://127.0.0.1:8765/report?job_id=demo&question=总结转化表现"
```

## L8 数据源

| 环境 | 配置 | 说明 |
|------|------|------|
| 本地 | 无 env | 自动 SQLite `data/l8_metrics.db` + seed |
| Postgres | `DATABASE_URL` / `POSTGRES_URL` | `docker compose --profile l8 up -d` |
| 查询 | `GET /modules/l8-analytics/source` | 当前数据源 |

```powershell
pip install -r requirements-db.txt   # Postgres 驱动
docker compose --profile l8 up -d
psql $POSTGRES_URL -f scripts/l8_schema.sql
```

## 扩展 API

| 接口 | 说明 |
|------|------|
| `POST /rag/kg/query` | 实体关系查询（竞品/达人/商品） |
| `POST /rag/estimate-cost` | ingest 前 token 预算 |
| `POST /rag/sync/l8` | L8 指标 → 分层 Tree 节点 |
| `GET /report?job_id=` | 带 job 的 L8 分层报表 |

## 八层自动集成

- **启动**：`rag_bootstrap_on_startup` 自动 ingest `data/knowledge/`
- **L1**：爬虫文本 auto-ingest + KG 三元组
- **L2**：`fetch_rag_context` 注入脚本生成
- **L6**：`rag_pii_compliance` 质检项
- **L8**：管线结束时 `sync_l8_to_rag`

## 成本优化（AGENT_REFERENCE §4.7 / §5）

1. 默认 stub 模式零 API 成本
2. `use_extractors=false` 跳过大模型元数据提取
3. `IngestionCache` 避免重复 ingest
4. 热点文档优先 extractors，低质内容仅 token 切分
5. 生产用 `BAAI/bge-small-zh-v1.5` 本地嵌入

## Dashboard

Web 控制台 **后台 API** Tab → 代理 `/api/rag/*`、`/api/modules/l8-analytics/*` → orchestrator。

## 开源仓库与 Git

LlamaIndex / Chroma / FastAPI 官方仓库、私有仓目录对照、版本 v1.0–v1.4 迭代说明见 **[GIT_REPOS.md](GIT_REPOS.md)**。
