> ⚠️ **部署摘要与排期见 [MASTER_PLAN.md](./MASTER_PLAN.md) 第 11–12 节**。本文为逐步操作手册.


> **文档索引**：本文件为分册说明；**唯一总览**见 [MASTER_PLAN.md](./MASTER_PLAN.md)（八层架构、排期、商业化与 API 清单）。
# AI 电商种草视频 SaaS — Vercel 一键部署指南

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

## 11. Dashboard 部署清单（apps/web）

按顺序完成以下步骤后再执行 `vercel deploy --prod`：

| 步骤 | 命令 / 操作 | 验证 |
|------|-------------|------|
| 1. 安装依赖 | 仓库根目录 `npm install` | 无 peer 冲突 |
| 2. 本地构建 | `npm run build:web` | 构建成功，无 TypeScript 错误 |
| 3. 环境变量模板 | 参考 `apps/web/.env.example` | 变量名与 Dashboard **设置** 页一致 |
| 4. Vercel CLI | `npm i -g vercel`（若未安装） | `vercel --version` 有输出 |
| 5. 关联项目 | 仓库根目录 `vercel link` | 生成 `.vercel/project.json` |
| 6. 拉取密钥 | `vercel env pull apps/web/.env.local` | 含 `AI_GATEWAY_API_KEY`（可选） |
| 7. 注入生产变量 | Dashboard → Settings → Environment Variables | `ORCHESTRATOR_URL` 指向 Railway Worker |
| 8. Root Directory | Dashboard → General → **Root Directory** 设为 `apps/web`（推荐） | 或使用根目录 `vercel.json` + `build:web` |
| 9. Preview 部署 | `vercel deploy` | `/` 与 `/dashboard` 可访问 |
| 10. 生产部署 | `vercel deploy --prod` | `/api/health` 200；设置页 Orchestrator 在线 |

**Orchestrator 说明**：Vercel 无法运行本地 `:8765` FastAPI。生产环境须将 `ORCHESTRATOR_URL` 设为 Railway / 自建 Worker 的 HTTPS 地址。

**无 VERCEL_TOKEN 时**：仅完成上述本地构建与文档准备，勿执行 `vercel deploy`；在 CI 或本机 `vercel login` 后再部署。

---

*文档由 `scripts/write_remaining_docs.py` 生成。*
