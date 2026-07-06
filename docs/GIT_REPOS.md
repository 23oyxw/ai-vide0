# Git 仓库与开源依赖

> 本项目依托 **LlamaIndex** 等开源仓库二次开发，用**私有 Git 仓库**管理整套 IntelliSafe-RAG + 八层编排工程。  
> 远程推送约定见 [REMOTES.md](REMOTES.md)。

---

## 一、官方开源代码仓库（拉取 / 参考）

| 组件 | GitHub | 在本项目中的用途 |
|------|--------|------------------|
| **LlamaIndex**（核心） | https://github.com/run-llama/llama_index | 分块、检索、索引、QueryEngine；`orchestrator/rag/indexes.py` 二次封装 |
| **Chroma**（向量库） | https://github.com/chroma-core/chroma | 本地向量持久化 `data/chroma_db/` |
| **FastAPI**（接口层） | https://github.com/tiangolo/fastapi | 编排层 `:8765`，`/rag/*`、`/pipeline/run` 等 |
| **Scrapy**（分布式爬虫，可选） | https://github.com/scrapy/scrapy | L1 热点层可扩展；当前 L1 用 `readers.load_from_web` + httpx |
| **BeautifulSoup** | Python 生态（PyPI） | 网页解析，配合 L1 抓取 |

**面试表述要点**：熟读 LlamaIndex 核心模块（Reader / NodeParser / Index / QueryEngine），在本仓库 `orchestrator/rag/` 做 stub 降级 + 生产路径双轨实现。

---

## 二、私有仓库：目录结构对照

你规划的 **IntelliSafe-RAG 独立工程** 与本 **Monorepo** 的映射如下（当前仓库已落地右侧路径）：

| 规划目录（独立仓） | 本仓库实际路径 | 说明 |
|-------------------|----------------|------|
| `rag_base.py` | `orchestrator/rag/service.py` + `pipeline.py` | RAG 核心逻辑 |
| `api_server.py` | `orchestrator/main.py` + `orchestrator/rag/router.py` | FastAPI：`/rag` `/monitor` `/report` |
| `crawler/hot_spider.py` | `orchestrator/modules/l1_crawler/` + `rag/readers.py` | L1 热点抓取 + auto-ingest |
| `data/knowledge/` | `data/knowledge/` | 商家知识库样例 |
| `data/chroma_db/` | `data/chroma_db/` | Chroma 持久化（运行时生成） |
| `utils/data_parse.py` | `orchestrator/rag/metadata_ops.py` + `splitters.py` | 清洗、切分、元数据 |
| `utils/monitor_check.py` | `orchestrator/rag/metadata_ops.py` + L6 | 广告法 + PII |
| `test/test_query.py` | `tests/test_query.py` + `tests/test_rag_api.py` | pytest / smoke |
| — | `apps/web/` | Next.js 薄控制台（代理后台 API） |
| — | `orchestrator/adapters/l8_store.py` | L8 SQLite / Postgres 指标 |

### 当前 Monorepo 顶层结构

```
ai-video-orchestrator/
├── .gitignore
├── requirements.txt          # 编排层基础依赖
├── requirements-rag.txt      # LlamaIndex + Chroma（可选）
├── requirements-db.txt         # Postgres L8（可选）
├── README.md
├── AGENT_REFERENCE.md
├── orchestrator/               # FastAPI 八层编排 + RAG
│   ├── main.py
│   ├── rag/                    # IntelliSafe-RAG 模块
│   └── modules/                # L1–L8 业务模块
├── apps/web/                   # 前端控制台（薄层）
├── data/
│   ├── knowledge/
│   ├── chroma_db/              # gitignore
│   └── l8_metrics.db           # gitignore
├── docs/                       # 部署、RAG、Git 文档
└── scripts/
    └── start-dev.ps1           # 一键启动前后端
```

---

## 三、`.gitignore` 要点

根目录 `.gitignore` 已包含：

```gitignore
__pycache__/
*.py[cod]
.env
.env.local
.venv/
venv/
node_modules/
.next/
data/jobs/
*.log
```

**建议额外忽略的运行时产物**（向量库、本地 DB、日志目录）：

```gitignore
data/chroma_db/
data/rag_cache/
*.db
logs/
```

> 面试说明：密钥走 `.env` / Vercel env pull，仓库零 secret。

---

## 四、Git 初始化与首次推送

### 新建独立 IntelliSafe-RAG 仓（从零）

```bash
cd IntelliSafe-RAG
git init
git add .
git commit -m "初始提交：IntelliSafe-RAG企业情报底座完整工程"
git remote add origin <你的远程仓库地址>
git branch -M main
git push -u origin main
```

### 本 Monorepo（已初始化）

远程已配置见 [REMOTES.md](REMOTES.md)：

```bash
cd C:\Users\oyxw\Projects\ai-video-orchestrator
git remote -v
git add .
git commit -m "docs: 补充 Git 仓库与版本迭代说明"
git push origin main
git push gitee main    # 镜像（可选）
```

推送前请配置 Git 用户（若尚未设置）：

```bash
git config user.email "you@example.com"
git config user.name "Your Name"
```

---

## 五、版本迭代规划

| 版本 | 目标 | 本仓库状态 |
|------|------|------------|
| **v1.0** | 基础 RAG 问答 + 多源文档读取 | ✅ `orchestrator/rag/` + `/rag/ingest` `/rag/query` |
| **v1.1** | 接入数据库，读取点击/转化/订单 | ✅ `l8_store.py` + `/modules/l8-analytics/*` |
| **v1.2** | 爬虫模块，自动抓取电商热点 | ✅ L1 crawler + `readers.load_from_web` + auto-ingest |
| **v1.3** | 内容监控 + 报表统计接口 | ✅ `/rag/check`、L6、`/report`、KG |
| **v1.4** | 封装八层架构 API，对接种草视频平台 | ✅ `/pipeline/run` + `apps/web` 控制台 |
| **v1.6** | RAG/L8 自动化验证 | ✅ `scripts/verify-rag.ps1` + `tests/test_rag_api.py` + `npm run verify:rag` |

后续可选：**v1.5** Clerk 鉴权 · **v1.7** Vercel 生产部署 · **v1.8** 完整 LlamaIndex + Chroma 生产路径（`pip install -r requirements-rag.txt`）。

---

## 六、精简总结（可写入 README / 面试）

本项目依托 [LlamaIndex](https://github.com/run-llama/llama_index) 开源仓库进行二次开发，自建私有 Git 代码仓库管理整套 IntelliSafe-RAG 情报系统；基于 [Chroma](https://github.com/chroma-core/chroma) 向量库、[FastAPI](https://github.com/tiangolo/fastapi) 接口框架实现能力落地，分版本迭代**爬虫、知识库、数据监控、报表**四大模块，最终输出标准化 API 供给种草视频平台后台调用。

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [RAG.md](RAG.md) | IntelliSafe-RAG 架构与 API |
| [REMOTES.md](REMOTES.md) | GitHub + Gitee 双远程 |
| [DEPLOY.md](DEPLOY.md) | Vercel 部署 |
| [AGENT_REFERENCE.md](../AGENT_REFERENCE.md) | Agent 策略与待办 |
