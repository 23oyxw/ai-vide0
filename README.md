# AI Video Orchestrator

**多模态 AI 种草视频一站式 SaaS** — 控制面（Next.js 15）+ 编排层（FastAPI + MCP）

> 完整愿景与架构排期见 **[docs/MASTER_PLAN.md](docs/MASTER_PLAN.md)**

## 仓库结构

```
apps/web/          Next.js 15 控制台（Vercel 部署）
orchestrator/      FastAPI 编排层 (:8765)
mcp/c4d-mcp/       Cinema 4D MCP
docs/              主文档
```

## Dashboard 控制台

访问 `/dashboard` — **5 步门控向导**（粘贴链接 → 抓取 → 写脚本 → 出片 → 看效果）：

| Tab | 功能 |
|-----|------|
| **一键出片** | 5 步向导：抓取 → 智能写脚本 → 快速/完整出片 |
| **AI 商品图** | L2 stub 生成主图/场景图/卖点图（自动预填抓取结果） |
| **效果数据** | L8 点击/转化/订单（绑定最近 job_id，10s 轮询） |

首页 `/` 自动跳转控制台。一键本地启动：`npm run dev` 或 `.\scripts\start-dev.ps1`。

### 5 步 Demo 流程

1. 运行 `npm run dev`（或 `.\scripts\start-dev.ps1`）→ 打开 http://localhost:3000/dashboard
2. **一键出片**：粘贴商品链接，或点行业模板（家居/美妆/鞋服）→ **抓取商品**
3. **智能写脚本** → 确认选题与大纲 → 选 **快速模式（~10s）** → **生成视频**
4. 出片成功后点 **查看效果数据** → 效果数据 Tab 自动显示 `job_id` 与点击指标
5. 可选：点 **生成 AI 商品图** → AI 商品图 Tab 已预填商品名/品类

### 故障排查

| 现象 | 处理 |
|------|------|
| 白屏 / 页面 404 | 前端 `.next` 缓存损坏 → `npm run dev:web:clean` 或重启 `start-dev.ps1`（会自动检测并 clean 重启） |
| 脚本优化 404 | 后台为旧进程 → `start-dev.ps1` 会检测缺少 `optimize-prompts` 并重启 :8765 |
| 商品图 404 | 同上，确认 OpenAPI 含 `/modules/l2-content/generate-product-image` |
| 后台离线 | 确认 `uvicorn orchestrator.main:app --port 8765` 运行；检查 `ORCHESTRATOR_URL` |
| 效果数据「待接入」 | L8 真实数据源未配置；快速模式仍会写入 sqlite demo 种子数据 |
| 网络中断 | 确认 :3000 与 :8765 均在监听（`start-dev.ps1` 健康检查） |

## 快速开始

### 1. 环境

```powershell
cd C:\Users\oyxw\Projects\ai-video-orchestrator
copy apps\web\.env.example apps\web\.env.local
copy .env.example .env
# 编辑 AI_GATEWAY_API_KEY、ORCHESTRATOR_URL 等
```

### 2. Web 控制台

```powershell
npm install
npm run dev:web
# → http://localhost:3000/dashboard
#   GET  /api/health
#   POST /api/chat          (AI Gateway streamText / stub)
#   POST /api/pipeline/run  (代理 orchestrator)
#   POST /api/rag/query     (知识库问答)
#   POST /api/rag/ingest    (导入 data/knowledge)
```

### 2b. RAG 知识库（可选 LlamaIndex）

```powershell
pip install -r requirements-rag.txt   # TreeIndex + KnowledgeGraph + Chroma
pip install -r requirements-db.txt    # Postgres L8 驱动（可选）
docker compose --profile l8 up -d     # 本地 Postgres
# POSTGRES_URL=postgresql://orchestrator:orchestrator@127.0.0.1:5432/ai_video
uvicorn orchestrator.main:app --reload --port 8765
```

### 3. FastAPI 编排层

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn orchestrator.main:app --reload --port 8765
# → http://127.0.0.1:8765/health
#   POST /pipeline/run
```

一键 Demo：`.\scripts\run-demo.ps1`

### 4. 构建 Web

```powershell
npm run build:web
```

## Monorepo 脚本

| 命令 | 说明 |
|------|------|
| `npm run dev` | 一键启动前后端（`scripts/start-dev.ps1`） |
| `npm run dev:web` | Next.js 开发服务器 |
| `npm run dev:api` | uvicorn :8765 |
| `npm run verify:rag` | RAG + L8 接口 smoke（~30s） |
| `npm run verify` | 全量 API 协议 + RAG（~3–5 min） |
| `npm run build:web` | 生产构建 |
| `npm run lint:web` | ESLint |

## 文档

| 文档 | 说明 |
|------|------|
| [MASTER_PLAN.md](docs/MASTER_PLAN.md) | **总览 + 架构排期** |
| [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | 执行摘要 |
| [TECH_STACK.md](docs/TECH_STACK.md) | 技术栈 |
| [DEPLOY.md](docs/DEPLOY.md) | Vercel 部署 |
| [RAG.md](docs/RAG.md) | IntelliSafe-RAG（LlamaIndex） |
| [GIT_REPOS.md](docs/GIT_REPOS.md) | **开源依赖 + 私有仓结构 + 版本迭代** |
| [REMOTES.md](docs/REMOTES.md) | GitHub / Gitee 双远程 |
| [AGENT_REFERENCE.md](AGENT_REFERENCE.md) | Agent 策略参考 |
| [TOOLING.md](docs/TOOLING.md) | 工具统计 |
| [POST_PRODUCTION_LOGIC.md](docs/POST_PRODUCTION_LOGIC.md) | **视频后期制作**工作流（15s 四段式） |

## Vercel 部署

根目录 `vercel.json` 指向 `apps/web`。详见 [docs/DEPLOY.md](docs/DEPLOY.md)。

```powershell
npm i -g vercel
vercel login
vercel link
vercel env pull apps/web/.env.local
vercel deploy --prod
```
