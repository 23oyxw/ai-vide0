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

访问 `/dashboard` 打开 SaaS 控制台（shadcn/ui + 深色主题）：

- **选题创作** — L1-L2 表单 stub（商品、受众、卖点）
- **视频生成** — 触发 L3-L4，POST `/api/pipeline/run` 代理 orchestrator
- **数据看板** — L8 占位图表与指标
- **设置** — Web / Orchestrator / AI Gateway 连通性检测
- **AI 助手** — 右侧栏 `useChat` 对接 `/api/chat`（需 `AI_GATEWAY_API_KEY`）

首页 `/` 提供进入控制台入口。

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
| `npm run dev:web` | Next.js 开发服务器 |
| `npm run build:web` | 生产构建 |
| `npm run lint:web` | ESLint |
| `npm run dev:orchestrator` | uvicorn :8765（需已激活 venv） |

## 文档

| 文档 | 说明 |
|------|------|
| [MASTER_PLAN.md](docs/MASTER_PLAN.md) | **总览 + 架构排期** |
| [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | 执行摘要 |
| [TECH_STACK.md](docs/TECH_STACK.md) | 技术栈 |
| [DEPLOY.md](docs/DEPLOY.md) | Vercel 部署 |
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
