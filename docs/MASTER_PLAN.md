# AI 种草视频 SaaS — 主文档索引

> **版本**：v3.0 · **仓库**：`ai-video-orchestrator`  
> **定位**：输入商品链接 → 输出多平台种草视频的全链路 B2B SaaS  
> **原则**：控制面 Vercel-first，渲染面外置 Worker（video-factory / C4D / AE）

---

## 文档导航

| 文档 | 内容 |
|------|------|
| [PROJECT_PLAN.md](./PROJECT_PLAN.md) | 执行摘要、6 周里程碑、商业化 |
| [TECH_STACK.md](./TECH_STACK.md) | Vercel 企业栈：Next.js 15、AI SDK、Gateway、Workflow、Postgres/KV/Blob |
| [DEPLOY.md](./DEPLOY.md) | Vercel 一键部署、环境变量、Railway Worker 回调 |
| [TOOLING.md](./TOOLING.md) | 8 层 → 工具映射、MCP 接入、编排器 API |
| [POST_PRODUCTION_LOGIC.md](./POST_PRODUCTION_LOGIC.md) | **视频后期制作**四段式管线（FFmpeg/C4D/AE） |
| [ARCHITECTURE_LOGIC.md](./ARCHITECTURE_LOGIC.md) | 阶段划分、层 DAG、状态机、失败回流、禁止事项 |

---

## 架构一页摘要

```
商家 / Agent (Cursor MCP · Cline · OpenClaw)
        │ MCP / HTTP
        ▼
┌─────────────────────────────────────────────────────────┐
│  控制面 · Vercel (apps/web)                              │
│  Next.js 15 · AI SDK · AI Gateway · Clerk · Workflow    │
│  Postgres · KV · Blob                                    │
└───────────────────────────┬─────────────────────────────┘
                            │ POST /api/pipeline/run → proxy
                            ▼
┌─────────────────────────────────────────────────────────┐
│  编排器 · FastAPI (orchestrator/) :8765                  │
│  L1–L8 Layer Registry + Adapters                         │
└───────────────────────────┬─────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
 video-factory        ai-koubo-platform      C4D MCP (mcp/c4d-mcp)
 L3 分镜 / L4 渲染     L2 文案 / L7 发布       L4 3D 无头渲染
```

### 三平面

| 平面 | 职责 | 运行环境 |
|------|------|----------|
| **控制面** | Dashboard、API、AI 编排、鉴权、Webhook | Vercel · `apps/web` |
| **数据面** | 关系数据、向量、对象存储、队列 | Postgres / Neon、KV、Blob |
| **渲染面** | 视频合成、C4D/AE、FFmpeg | Railway / 本地 i9 · `video-factory` |

### 八层管线（L1–L8）

| 层 | 职责 | 主要工具 |
|----|------|----------|
| L1 | 爬虫 / 选品 | fetch MCP · `layers/l1_crawler.py` |
| L2 | 文案 / 脚本 | DeepSeek · ai-koubo · AI Gateway |
| L3 | 分镜 YAML | video-factory demos |
| L4 | 渲染 | video-factory · C4D · AE · FFmpeg |
| L5 | 调度 | FastAPI orchestrator · Workflow |
| L6 | 质检 / RAG | `/monitor` · pgvector（待接） |
| L7 | 发布 | ai-koubo publish |
| L8 | 数据看板 | Postgres · ECharts |

---

## 仓库结构

```
ai-video-orchestrator/
├── apps/web/              # Next.js 15 控制面（Vercel 部署入口）
├── orchestrator/          # FastAPI 八层编排器 (:8765)
├── mcp/c4d-mcp/           # Cinema 4D MCP 服务
├── docs/                  # 本文档集
├── config/                # Cursor/Cline MCP 配置片段
└── scripts/               # setup / demo 脚本
```

---

## 快速启动

### Web（控制面）

```powershell
cd C:\Users\oyxw\Projects\ai-video-orchestrator
copy .env.example .env
npm install
npm run dev:web
# → http://localhost:3000
```

### Orchestrator（编排器）

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn orchestrator.main:app --reload --port 8765
# → http://127.0.0.1:8765/health
```

---

## API 路由对照（脚手架）

| 端点 | 层 | 说明 |
|------|-----|------|
| `GET /api/health` | — | Web 健康检查 |
| `POST /api/chat` | L2 | AI Gateway `streamText` stub |
| `POST /api/pipeline/run` | L5 | 代理 → orchestrator `/pipeline/run` |
| `GET /health` | — | Orchestrator 健康（:8765） |
| `POST /pipeline/run` | L1–L8 | 八层管线执行 |

---

## 6 周里程碑（摘要）

| 周 | 交付 |
|----|------|
| W1 | Next.js + Clerk + Postgres + Dashboard |
| W2 | L1–L3 + Gateway + ai-koubo |
| W3 | Workflow + video-factory + Webhook |
| W4 | RAG + L6/L7 + Blob 发布 |
| W5 | L8 看板 + 爆款逆向 MVP |
| W6 | 端到端 Demo + Preview 上线 |

> 详细排期与 API 附录见各分册；技术细节以 [TECH_STACK.md](./TECH_STACK.md) 为准。

---

## 环境变量（核心）

| 变量 | 用途 |
|------|------|
| `AI_GATEWAY_API_KEY` | Vercel AI Gateway |
| `DATABASE_URL` / `POSTGRES_URL` | Postgres |
| `ORCHESTRATOR_URL` | Web 代理编排器（默认 `http://127.0.0.1:8765`） |
| `VIDEO_FACTORY_PATH` | L3/L4 外部项目 |
| `AI_KOUBO_PATH` | L2/L7 外部项目 |
| `C4D_ROOT` | Cinema 4D 安装目录 |

完整列表见根目录 [.env.example](../.env.example) 与 [DEPLOY.md](./DEPLOY.md)。

---

---

## 架构逻辑（后期开发约束）

阶段划分（脚手架 / 联调 / 生产）、L1→L8 依赖 DAG、Job 状态机、L6→L2 失败回流、L8→L1/L2 数据闭环，以及「禁止在 Vercel 调 C4D / 禁止 OpenClaw 作生产调度」等规则，**以 [ARCHITECTURE_LOGIC.md](./ARCHITECTURE_LOGIC.md) 为准**；本文档仅保留索引与排期，不重复展开。

## 当前脚手架状态

- [x] FastAPI orchestrator + 8 层 stub + C4D MCP
- [x] `apps/web` Next.js 15 + AI SDK stub routes
- [x] Monorepo `package.json` workspaces
- [ ] Clerk 鉴权 · Postgres schema · Vercel Workflow
- [ ] 真实 L1–L8 业务逻辑与 Worker Webhook

**下一步精修**：Clerk + Dashboard UI、Gateway 接通真实模型、Workflow 串联 L4 渲染 Worker。
