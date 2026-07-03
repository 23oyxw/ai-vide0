from pathlib import Path

ROOT = Path(r"C:\Users\oyxw\Projects\ai-video-orchestrator")
DOCS = ROOT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)

TECH_STACK = r"""# AI 电商种草视频 SaaS — 技术栈说明

> **版本**：v1.0（Vercel 企业级云原生）
> **定位**：多租户 B2B 种草视频生成与编排平台
> **原则**：控制面在 Vercel，渲染面在外部 Worker；Webhook + 队列解耦

---

## 1. 架构总览

| 平面 | 职责 | 运行环境 |
|------|------|----------|
| **控制面（Control Plane）** | Dashboard、API、AI 编排、鉴权、任务调度、Webhook 接收 | Vercel（Next.js 15） |
| **数据面（Data Plane）** | 关系数据、向量检索、对象存储、缓存队列 | Vercel Postgres / Neon、KV、Blob |
| **渲染面（Render Plane）** | 视频合成、C4D/AE 批渲染、FFmpeg 重编码 | Railway / Fly.io / 本地 i9 渲染节点 |

```mermaid
flowchart LR
  subgraph Vercel["控制面 · Vercel"]
    APP[Next.js 15 App Router]
    WF[Vercel Workflow]
    GW[AI Gateway]
    DB[(Postgres + pgvector)]
    KV[(Vercel KV)]
    BL[(Vercel Blob)]
  end
  subgraph External["渲染面 · 外部"]
    PY[video-factory Python Worker]
    C4D[C4D Commandline]
    AE[AE aerender]
  end
  APP --> GW
  APP --> WF
  WF --> KV
  WF --> PY
  PY --> C4D
  PY --> AE
  PY -->|Webhook| APP
  APP --> DB
  APP --> BL
```

**不在 Vercel 上运行**：长耗时视频管线、C4D 无头渲染、AE aerender、大规模 FFmpeg — 全部通过队列下发至外部 Worker，完成后 HTTP Webhook 回写任务状态。

---

## 2. 前端 / 全栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 框架 | **Next.js 15 App Router** | Vercel 原生部署；Server/Client 组件边界清晰 |
| UI 生成 | **v0.dev** | Dashboard、表单、数据表格的快速迭代与 design token 对齐 |
| 组件库 | **shadcn/ui + Tailwind CSS** | 可访问性、主题、与 v0 输出一致 |
| 渲染模型 | **React Server Components (RSC)** | 默认服务端渲染；敏感逻辑与数据获取不进入客户端 bundle |
| 数据变更 | **Server Actions** | 表单提交、任务创建、租户配置变更 |
| API | **Route Handlers** | Webhook、第三方回调、流式 AI 响应 |

**推荐目录结构（示意）**

- `app/(dashboard)/` — 商家与运营台
- `app/api/` — Route Handlers（含 `/api/webhooks/render`）
- `components/ui/` — shadcn 组件
- `lib/ai/` — AI SDK 封装与 Gateway 配置

---

## 3. AI 层

### 3.1 Vercel AI SDK（`ai` 包）

| API | 用途 |
|-----|------|
| `useChat` | 商家侧对话式脚本/创意助手（Client） |
| `useObject` | 流式结构化 UI（分镜、商品卖点 JSON） |
| `streamText` | 长文案、口播稿流式生成（Route Handler / Server Action） |
| `generateObject` | 一次性结构化输出（分镜 YAML、质检规则） |
| **v6 注意** | 结构化输出推荐 `generateText` + `Output.object()` 替代部分 `generateObject` 用法，与 Gateway 模型能力对齐 |

### 3.2 Vercel AI Gateway

- **单一端点** 路由 OpenAI、Anthropic、DeepSeek、Google 等，统一鉴权、限流与可观测性
- 应用内通过 `baseURL` + Gateway API Key（或 Vercel OIDC 集成）调用，避免在代码中散落多厂商 Key
- 按环境（Production / Preview）在 Vercel 项目设置中配置不同 Gateway 路由策略

### 3.3 模型与 Provider 配置表

| 场景 | 推荐模型 | Provider（经 Gateway） | 备注 |
|------|----------|------------------------|------|
| 口播/种草文案 | DeepSeek V3 / GPT-4o mini | DeepSeek / OpenAI | 成本与中文表现平衡 |
| 分镜与结构化脚本 | Claude Sonnet / GPT-4o | Anthropic / OpenAI | `Output.object` 约束 schema |
| 多模态商品理解 | Gemini 1.5 Pro | Google | 商品图 + 描述联合理解 |
| Embedding | text-embedding-3-small 或 Gateway 等价物 | OpenAI / 托管 embedding | 与 pgvector 维度一致 |
| 运营质检摘要 | Claude Haiku / 小模型 | Anthropic | 低成本批量 |

环境变量示例（名称示意，勿提交真实密钥）：`AI_GATEWAY_URL`、`AI_GATEWAY_API_KEY`、各 Provider 在 Gateway 控制台侧绑定。

---

## 4. 后端 / 编排

| 能力 | 首选 | 备选 |
|------|------|------|
| 同步 API | Next.js **Route Handlers** | — |
| 突变与表单 | **Server Actions** | — |
| 长任务编排 | **Vercel Workflow**（首选） | Inngest、Trigger.dev |
| 重计算 / 视频 | **Python Worker**（Railway / Fly.io） | 自建 K8s Job |

**编排模式**

1. 用户提交「生成种草视频」→ Server Action 写入 Postgres 任务 + KV 队列
2. Workflow 步骤：AI 生成分镜 → 校验 → 推送 `render_job` 至外部 Worker
3. Worker 完成后 `POST /api/webhooks/render` → 更新 Blob URL、触发 L6 质检 Workflow
4. 失败重试与死信：KV 记录 attempt，Workflow 补偿或人工 ops 介入

---

## 5. 数据层（L8）

| 存储 | 用途 |
|------|------|
| **Vercel Postgres** 或 **Neon** | 租户、订单、任务、分镜版本、RBAC |
| **Vercel KV / Redis** | 渲染队列、幂等键、速率限制、短期任务状态 |
| **Vercel Blob** | 成片、中间素材、缩略图、导出包 |
| **Vercel Analytics** + **ECharts** | 产品埋点 + 运营大屏（转化率、渲染耗时、失败率） |

**迁移与分支**：Preview 环境使用 Neon branch 或独立 Postgres 实例，避免 PR 污染生产数据。

---

## 6. RAG 与 IntelliSafe（智能安全）

| 组件 | 选型 |
|------|------|
| 向量库 | **pgvector**（与 Postgres 同库）或 Pinecone / **Upstash Vector** |
| 嵌入 | AI SDK `embed` / `embedMany` + Gateway 路由的 embedding 模型 |
| 知识源 | 品牌调性指南、违禁词库、平台审核规则、历史高分脚本 |

**典型流程**

1. 文档切块 → `embedMany` → 写入向量表（带 `tenant_id`）
2. 生成前 RAG 检索 → 注入 system prompt
3. 生成后规则 + 小模型二次审核（IntelliSafe），不通过则 Workflow 回滚至人工审核节点

---

## 7. 渲染管线（外部）

| 组件 | 角色 |
|------|------|
| **video-factory**（Python Worker） | 编排 YAML 分镜、调用下游渲染器、上传 Blob、回调 Vercel |
| **C4D Commandline** | 3D 产品场景、模板化镜头（i9 或专用渲染节点） |
| **AE aerender** | 动效包装、字幕轨、品牌模板合成 |
| **Webhook** | `Authorization` + 签名验证；payload 含 `job_id`、`status`、`artifact_urls` |

**约束**：单 Job 超时、并发上限在 Worker 侧配置；Vercel 仅保存元数据与 URL，不持有大文件内存。

---

## 8. 鉴权与多租户

| 方案 | 适用 |
|------|------|
| **NextAuth.js v5**（Auth.js） | 自建 IdP、Credentials/OAuth、与 Postgres 用户表深度集成 |
| **Clerk Enterprise** | 快速上线 SSO、组织（Organization）即租户、合规需求 |

**RBAC 角色（示意）**

| 角色 | 权限 |
|------|------|
| `merchant` | 本租户商品、任务、成片下载 |
| `ops` | 跨租户任务监控、重试、质检队列 |
| `admin` | 租户开通、Gateway 配额、系统配置 |

所有 API 与 Server Actions 必须校验 `tenant_id`，向量与 Blob 路径带租户前缀。

---

## 9. 部署与运维

生产与预览环境的一键部署、环境变量（含 AI Gateway OIDC）、外部 Worker 与 PR Preview 流程见 **[DEPLOY.md](./DEPLOY.md)**。

---

## 10. 技术决策摘要

- **云原生控制面**：Next.js 15 on Vercel，AI Gateway 统一模型入口，Workflow 负责可靠编排
- **渲染面外置**：视频/C4D/AE 不进 Serverless 函数，避免超时与冷启动
- **Webhook + 队列**：异步边界清晰，可水平扩展 Worker
- **专业工程取向**：可观测（Analytics + 结构化日志）、多租户 RBAC、RAG + 生成后审核，面向企业客户交付

---

*文档由 `scripts/write_remaining_docs.py` 生成，与仓库 `PROJECT_PLAN.md` 架构分层一致。*
"""

DEPLOY = r"""# AI 电商种草视频 SaaS — Vercel 一键部署指南

> **目标**：面试/演示可复现的端到端部署流程（控制面 Vercel + 渲染面 Railway）
> **安全**：示例仅使用占位符；真实密钥通过 Vercel 控制台与 `vercel env pull` 管理

---

## 1. 前置条件

| 工具 | 用途 |
|------|------|
| [Node.js 20+](https://nodejs.org/) | Next.js 本地构建 |
| [Vercel CLI](https://vercel.com/docs/cli) | `vercel link` / `vercel deploy` |
| [Git](https://git-scm.com/) | 与 GitHub/GitLab 集成 PR Preview |
| Railway CLI（可选） | 外部 Python Worker 部署 |
| Vercel 团队账号 | AI Gateway、Postgres、KV、Blob 开通 |

```bash
npm i -g vercel
vercel login
```

---

## 2. 关联 Vercel 项目

在 Next.js 应用根目录（本 monorepo 中即为部署入口仓库根目录）执行：

```bash
cd C:\Users\oyxw\Projects\ai-video-orchestrator
vercel link
```

交互提示：

1. 选择 Team / Personal
2. **Link to existing project** 或 **Create new project**
3. 确认 Framework Preset 为 **Next.js**
4. 根目录与 Build Command 保持默认（`next build`）除非 monorepo 另有说明

关联完成后，项目根目录会出现 `.vercel/project.json`（勿提交敏感内容，可按团队规范 gitignore）。

---

## 3. 配置环境变量

### 3.1 AI Gateway（推荐 OIDC / 集成方式）

在 [Vercel Dashboard](https://vercel.com) → Project → **Settings → Environment Variables** 添加：

| 变量名 | 环境 | 说明 |
|--------|------|------|
| `AI_GATEWAY_URL` | Production, Preview, Development | Gateway 基址（控制台复制） |
| `AI_GATEWAY_API_KEY` | Production, Preview | Gateway 令牌；Development 可用 `vercel env pull` |
| `OPENAI_API_KEY` 等 | — | **优先在 Gateway 控制台绑定 Provider**，应用侧仅 Gateway Key |

**本地开发（无硬编码密钥）**

```bash
vercel env pull .env.local
```

该文件应已在 `.gitignore` 中；面试演示时说明：「密钥来自 Vercel OIDC / env pull，仓库零 secret」。

### 3.2 数据与存储

| 变量名 | 说明 |
|--------|------|
| `POSTGRES_URL` | Vercel Postgres 或 Neon 连接串 |
| `KV_REST_API_URL` / `KV_REST_API_TOKEN` | Vercel KV（任务队列） |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob 读写 |
| `NEXTAUTH_SECRET` 或 Clerk `CLERK_*` | 鉴权（二选一方案） |
| `WEBHOOK_SECRET` | 渲染 Worker 回调签名校验 |
| `RENDER_WORKER_URL` | Railway 上 video-factory 基址 |

### 3.3 外部 Worker 回调

Vercel Production URL 固定后，在 Railway 配置：

```bash
CALLBACK_URL=https://<your-project>.vercel.app/api/webhooks/render
WEBHOOK_SECRET=<与 Vercel 相同>
```

---

## 4. 首次生产部署

```bash
vercel deploy --prod
```

CLI 输出 Production URL。验证清单：

- [ ] `/` Dashboard 可访问
- [ ] 健康检查 Route（如有）返回 200
- [ ] AI Gateway 测试接口（仅 staging 文案）流式正常
- [ ] Postgres 迁移已执行（`drizzle-kit push` / `prisma migrate deploy` 按项目脚本）

**面试话术要点**：控制面单次部署 < 5 分钟；渲染能力不阻塞 Vercel 构建。

---

## 5. Preview 部署（每个 PR）

1. 将 Vercel 项目连接 Git 仓库（Dashboard → Git）
2. 开启 **Pull Request Comments** 与 **Preview Deployments**
3. 提交 PR 后自动 `vercel deploy` Preview URL

```bash
git checkout -b feat/ai-storyboard
git push -u origin feat/ai-storyboard
# 打开 PR → Vercel bot 评论 Preview 链接
```

Preview 环境变量继承 Project 的 Preview scope；数据库建议使用 **Neon branch** 或只读副本，避免写生产。

演示命令（可选，本地模拟 Preview）：

```bash
vercel deploy
# 非 --prod 即为 Preview
```

---

## 6. 外部 Worker：Railway 部署（video-factory）

> 视频/C4D/AE 不在 Vercel 运行；本节为渲染面标准步骤。

### 6.1 准备

- Docker 或 Railway Nixpacks 检测到 `requirements.txt` 的 Python 服务
- 仓库内 Worker 入口（示例）：`orchestrator/` 或独立 `workers/video-factory/`

### 6.2 CLI 流程（示意）

```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

Railway 变量：

| 变量 | 值 |
|------|-----|
| `VERCEL_WEBHOOK_URL` | `https://xxx.vercel.app/api/webhooks/render` |
| `WEBHOOK_SECRET` | 与 Vercel 一致 |
| `BLOB_*` 或 S3 兼容 | 大文件直传 Blob（可选 SDK） |

### 6.3 C4D / AE 节点

- **C4D Commandline**、**aerender** 安装在 Windows i9 或专用渲染机
- Worker 通过 Redis/KV 拉取 job，SSH/Agent 触发本地 CLI（架构见 `TECH_STACK.md`）
- 面试说明：云控制面 + 混合渲染节点是企业常见形态

---

## 7. 端到端演示脚本（面试向）

按顺序口述并操作：

1. **`vercel link`** — 项目与团队绑定
2. **`vercel env pull .env.local`** — 本地无 secret 泄露
3. **本地** `pnpm dev` — 验证 AI Gateway 流式
4. **`vercel deploy`** — Preview URL 给面试官
5. **提交任务** — Dashboard 创建种草视频 → KV 队列有 job
6. **Railway Worker** 消费 → 模拟或真实渲染 → **Webhook** 回 Vercel
7. **Blob** 页面展示成片 → Analytics 可见请求

---

## 8. 回滚与故障排查

| 现象 | 排查 |
|------|------|
| AI 401 | Gateway Key / env 是否仅 Production；Preview 是否同步变量 |
| 函数超时 | 确认重任务未在 Route Handler 内做渲染，应只入队 |
| Webhook 403 | `WEBHOOK_SECRET`、签名头、时钟偏差 |
| DB 连接失败 | Preview 是否误连 Production `POSTGRES_URL` |

回滚生产：

```bash
vercel rollback
# 或在 Dashboard → Deployments → Promote 上一版本
```

---

## 9. 与 TECH_STACK 的对应关系

| 文档章节 | 部署动作 |
|----------|----------|
| 控制面 Vercel | `vercel deploy --prod` |
| AI Gateway | Dashboard + `vercel env pull` |
| Postgres / KV / Blob | Vercel Storage 集成一键注入 env |
| 渲染面 | Railway `railway up` + Webhook |
| 多租户鉴权 | Clerk / NextAuth env 在 Vercel 分环境配置 |

详细选型见 **[TECH_STACK.md](./TECH_STACK.md)**。

---

## 10. 检查清单（交付前）

- [ ] `.env.local` / `.env` 未提交 Git
- [ ] Production 与 Preview 变量已区分
- [ ] AI Gateway Provider 在控制台配置完成
- [ ] Webhook URL 使用 HTTPS 且与 Worker 一致
- [ ] PR Preview 自动评论可用
- [ ] 监控：Vercel Analytics + 错误日志（可接 Sentry）

---

*文档由 `scripts/write_remaining_docs.py` 生成。*
"""

PROJECT_PLAN = r"""# AI 种草视频 SaaS — 项目计划书

> **版本**：v2.0（Vercel-first 云原生架构）
> **定位**：企业级 AI 电商种草视频生产平台
> **核心原则**：控制面在 Vercel，渲染面在外部 Worker

---

## 1. 项目愿景与定位

### 1.1 愿景

为电商商家与 MCN 机构提供 **「一键种草视频」** 生产能力：从商品链接到多平台可发布短视频，全流程 AI 驱动、可审计、可规模化。

### 1.2 产品定位

| 维度 | 描述 |
|------|------|
| **目标用户** | 中小电商商家、品牌运营、MCN 内容团队 |
| **核心价值** | 降低种草视频制作成本 80%+，缩短交付周期从天级到小时级 |
| **差异化** | 八层流水线 + Vercel 云原生控制面 + 专业渲染 Worker 分离 |
| **技术路线** | Next.js 15 + Vercel AI SDK + AI Gateway + Workflow |

### 1.3 架构分层原则

```
控制面（Vercel）：UI · API · AI · 数据 · 鉴权 · 工作流编排
        │
        │ Webhook + Queue
        ▼
渲染面（外部 Worker）：video-factory · C4D Commandline · AE aerender · FFmpeg
```

**不在 Vercel 上跑重计算**：视频合成、3D 渲染、长时间 FFmpeg 任务全部下沉到 Railway / Fly.io / 本地 i9 渲染机。

---

## 2. 八层架构 → Vercel 技术映射表

| 层级 | 业务职责 | 原方案（工具统筹） | Vercel-first 映射 | 运行时 |
|------|----------|-------------------|-------------------|--------|
| **L1 爬虫** | 商品/竞品/评论采集 | Python + fetch MCP | Route Handler + Cron；复杂爬虫走外部 Worker | Vercel Functions |
| **L2 内容** | 文案/脚本/口播稿 | DeepSeek via ai-koubo | AI SDK `streamText` + AI Gateway | Vercel Serverless |
| **L3 分镜** | 分镜 YAML | video-factory YAML | `generateText` + `Output.object()` | Vercel Serverless |
| **L4 渲染** | 视频合成/3D | video-factory + C4D | 外部 Worker + Webhook 回调 | Railway / i9 |
| **L5 调度** | 任务编排/队列 | FastAPI + Agent | **Vercel Workflow**（首选）或 Inngest | Vercel Workflow |
| **L6 质检** | QA/合规 RAG | RAG stub + /monitor | pgvector + `embed`；Workflow Hook 审批 | Postgres |
| **L7 发布** | 多平台分发 | ai-koubo publish | Server Actions + ai-koubo API | Vercel Serverless |
| **L8 数据** | 指标看板 | MySQL + ECharts | Postgres + Analytics + ECharts | Vercel + Neon |

### 2.1 与现有仓库的关系

| 仓库 | 角色 | 迁移策略 |
|------|------|----------|
| `ai-video-orchestrator` | 编排中枢 → Next.js 15 控制面 | 新建 `apps/web`，Python 层保留为 Worker 适配 |
| `ai-koubo-platform` | L2 内容 + L7 发布 | API 集成，逐步内聚 AI Gateway |
| `video-factory` | L3/L4 渲染引擎 | Railway Worker + Webhook |

---

## 3. 系统架构图

```mermaid
flowchart TB
    subgraph Client["客户端"]
        Merchant["商家 Dashboard"]
        Ops["运营后台"]
        Admin["管理控制台"]
    end
    subgraph Vercel["控制面 · Vercel"]
        Next["Next.js 15 App Router"]
        Auth["Clerk / Auth.js v5"]
        API["Route Handlers + Server Actions"]
        WDK["Vercel Workflow"]
        AISDK["Vercel AI SDK"]
        Gateway["AI Gateway"]
        Blob["Vercel Blob"]
        KV["Vercel KV"]
        PG["Postgres + pgvector"]
    end
    subgraph Workers["渲染面 · 外部 Worker"]
        VF["video-factory · Railway"]
        C4D["C4D Commandline · i9"]
        AE["AE aerender"]
    end
    subgraph External["外部服务"]
        Koubo["ai-koubo-platform"]
        Platforms["抖音 / 小红书 / 视频号"]
    end
    Merchant --> Next
    Ops --> Next
    Admin --> Next
    Next --> Auth
    Next --> API
    API --> WDK
    WDK --> AISDK
    AISDK --> Gateway
    WDK --> KV
    WDK --> PG
    WDK --> VF
    VF --> C4D
    VF --> AE
    VF -->|Webhook| API
    API --> Blob
    WDK --> Koubo
    Koubo --> Platforms
    PG --> Next
```

### 3.1 种草视频流水线时序

```mermaid
sequenceDiagram
    participant U as 商家
    participant N as Next.js API
    participant W as Vercel Workflow
    participant G as AI Gateway
    participant R as Render Worker
    participant P as Postgres
    U->>N: 提交商品链接
    N->>W: start(videoPipeline)
    W->>G: L1-L3 采集/脚本/分镜
    W->>P: 持久化任务
    W->>R: 派发渲染 + Webhook token
    R->>N: Webhook 成片完成
    N->>W: resumeHook(render-done)
    W->>G: L6 RAG 合规质检
    alt 人工审批
        W->>W: createHook 等待运营
        U->>N: 审批通过
        N->>W: resumeHook(approved)
    end
    W->>N: L7 ai-koubo 发布
    W->>P: L8 指标回写
```

---

## 4. 与市面工具差异

### 4.1 不采用的路径

| 方案 | 问题 | 我们的选择 |
|------|------|-----------|
| 本地 Agent 编排 | 难多租户、难一键云部署 | **Vercel Workflow** |
| 直连各厂商 API | 无 Failover、无成本归因 | **Vercel AI Gateway** |
| FastAPI 单体扛渲染 | Functions 超时（≤300s） | **控制面/渲染面分离** |
| 纯无代码视频工具 | 无法 C4D/定制分镜 | **video-factory 可编程管线** |

### 4.2 核心竞争力

1. 八层可观测流水线（AI Gateway `tags` 成本归因）
2. 多模型策略：脚本 DeepSeek、质检 Claude、图像 Gemini
3. Durable Workflow：断网不丢任务 + 人工审批 Hook
4. 专业渲染栈：C4D / AE 服务高端品牌
5. 一键 `vercel deploy` + PR Preview

---

## 5. 商业化三层

### 5.1 产品层（SaaS 套餐）

| 套餐 | 月费 | 视频额度 | AI 模型 | 渲染 | 发布平台 |
|------|------|----------|---------|------|----------|
| **Starter** | ¥299 | 30 条/月 | DeepSeek + Gemini Flash | 标准模板 | 1 平台 |
| **Growth** | ¥999 | 150 条/月 | + Claude Sonnet | + C4D 3D | 3 平台 |
| **Enterprise** | 定制 | 无限 | 全模型 + BYOK | 专属渲染节点 | 全平台 + API |

### 5.2 技术层（成本结构）

- **AI Gateway**：按 Token（零加价），分层模型路由
- **Vercel 托管**：Pro/Enterprise 席位 + Blob CDN
- **渲染 Worker**：Railway CPU 时长 + i9 本地 C4D
- **存储**：Blob + Postgres 按量，成片 30 天生命周期

### 5.3 交付层（客户成功）

- Onboarding ≤ 15 分钟
- Growth 以上 99.5% API SLA
- Enterprise 白标 + Clerk Organization 多租户

---

## 6. 六周排期（Vercel-first）

| 周次 | 重点任务 | 里程碑 |
|------|----------|--------|
| **W1** | Next.js 15 + shadcn + Clerk + Postgres Schema | Dashboard 可 `vercel deploy` 登录 |
| **W2** | AI SDK L1-L3 + v0.dev UI + Gateway tags | 商品 URL → 脚本 + 分镜 YAML |
| **W3** | Vercel Workflow L5 + KV 队列 + Hook 审批 | 端到端编排（Mock 渲染） |
| **W4** | video-factory Railway + Webhook + Blob | 真实渲染一条种草视频 |
| **W5** | pgvector RAG L6 + ai-koubo L7 + ECharts L8 | 八层 Production Ready |
| **W6** | PR Preview CI + Gateway 预算告警 + 安全审计 | Production 上线 |

---

## 7. 面试口述版（3 分钟）

> **开场（15s）**  
> 我做 AI 电商种草视频 SaaS：商家输入商品链接，系统完成采集、脚本、分镜、渲染、质检、发布，输出可投放短视频。

> **架构亮点（60s）**  
> 控制面在 Vercel：Next.js 15 Dashboard、AI SDK + AI Gateway 统一路由 DeepSeek/Claude/Gemini，自带 Failover 和成本归因。长编排用 Vercel Workflow，`use step` 逐步重试，`createHook` 人工审批，页面刷新任务不丢。渲染面下沉外部 Worker（video-factory on Railway、C4D on i9），Webhook 回调恢复 Workflow。

> **八层设计（45s）**  
> L1 爬虫、L2 脚本、L3 分镜、L4 外部渲染、L5 Workflow、L6 pgvector RAG 质检、L7 ai-koubo 发布、L8 Postgres + ECharts 看板。每层有明确 Vercel 技术映射。

> **差异化（30s）**  
> 对比 Agent 方案和无代码工具：企业级 `vercel deploy`、多租户 RBAC、全链路可观测、可编程 C4D/FFmpeg 管线。商业化 Starter/Growth/Enterprise 三档。

> **收尾（10s）**  
> 六周排期已规划；现有 Python orchestrator 八层适配器平滑迁移为 Worker 实现。

---

## 附录 A：风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Vercel Functions 超时 | 渲染面分离；Workflow 异步等 Webhook |
| AI Gateway 预算超限 | 告警 + HTTP 402 降级 + 小模型兜底 |
| C4D 渲染机单点 | 队列削峰 + 多渲染节点注册 |
| 平台发布 API 变更 | ai-koubo 抽象层 + 版本化 Adapter |

## 附录 B：成功指标（KPI）

| 指标 | Week 6 目标 | 三个月目标 |
|------|-------------|------------|
| 端到端成功率 | ≥ 85% | ≥ 95% |
| 平均生成时长 | ≤ 30 min | ≤ 15 min |
| AI 成本/条 | ≤ ¥2 | ≤ ¥1 |
| 商家 NPS | — | ≥ 40 |

---

*详见 [TECH_STACK.md](./TECH_STACK.md) 与 [DEPLOY.md](./DEPLOY.md)。*
"""


def write_utf8(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    plan_path = DOCS / "PROJECT_PLAN.md"
    tech_path = DOCS / "TECH_STACK.md"
    deploy_path = DOCS / "DEPLOY.md"
    write_utf8(plan_path, PROJECT_PLAN.strip() + "\n")
    write_utf8(tech_path, TECH_STACK.strip() + "\n")
    write_utf8(deploy_path, DEPLOY.strip() + "\n")
    for p in (plan_path, tech_path, deploy_path):
        lines = p.read_text(encoding="utf-8").splitlines()
        print(f"Wrote {p} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
