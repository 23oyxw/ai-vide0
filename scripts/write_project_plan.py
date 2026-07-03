from pathlib import Path

ROOT = Path(r"C:\Users\oyxw\Projects\ai-video-orchestrator\docs")
ROOT.mkdir(parents=True, exist_ok=True)

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

控制面（Vercel）：UI、API、AI、数据、鉴权、工作流编排
渲染面（外部 Worker）：video-factory、C4D Commandline、AE aerender、FFmpeg

不在 Vercel 上跑重计算：视频合成、3D 渲染、长时间 FFmpeg 全部下沉到 Railway / Fly.io / 本地 i9。

---

## 2. 八层架构 → Vercel 技术映射表

| 层级 | 业务职责 | 原方案 | Vercel-first 映射 | 运行时 |
|------|----------|--------|-------------------|--------|
| L1 爬虫 | 商品/竞品采集 | Python + fetch MCP | Route Handler + Cron + 外部 Worker | Vercel Functions |
| L2 内容 | 文案/脚本 | DeepSeek / ai-koubo | AI SDK streamText + AI Gateway | Vercel Serverless |
| L3 分镜 | 分镜 YAML | video-factory YAML | generateText + Output.object() | Vercel Serverless |
| L4 渲染 | 视频/3D | video-factory + C4D | 外部 Worker + Webhook | Railway / i9 |
| L5 调度 | 编排/队列 | FastAPI + Agent | Vercel Workflow / Inngest | Vercel Workflow |
| L6 质检 | QA/RAG | RAG stub | pgvector + embed；Workflow Hook | Postgres |
| L7 发布 | 多平台 | ai-koubo publish | Server Actions + ai-koubo API | Vercel Serverless |
| L8 数据 | 看板 | MySQL + ECharts | Postgres + Analytics + ECharts | Vercel + Neon |

### 2.1 仓库关系

- ai-video-orchestrator：升级为 Next.js 15 控制面，保留 Python Worker 适配
- ai-koubo-platform：L2/L7 API 服务，逐步内聚 AI Gateway
- video-factory：L3/L4 渲染引擎，部署 Railway

---

## 3. 系统架构图

```mermaid
flowchart TB
    subgraph Client
        M[商家 Dashboard]
        O[运营后台]
    end
    subgraph Vercel
        N[Next.js 15]
        W[Vercel Workflow]
        G[AI Gateway]
        P[Postgres + pgvector]
        K[Vercel KV]
        B[Vercel Blob]
    end
    subgraph Workers
        VF[video-factory]
        C4D[C4D Commandline]
    end
    M --> N
    O --> N
    N --> W
    W --> G
    W --> K
    W --> P
    W --> VF
    VF --> C4D
    VF -->|Webhook| N
    N --> B
```

### 3.1 流水线时序

```mermaid
sequenceDiagram
    participant U as 商家
    participant API as Next.js API
    participant WF as Workflow
    participant GW as AI Gateway
    participant RW as Render Worker
    U->>API: 提交商品链接
    API->>WF: start(videoPipeline)
    WF->>GW: L1-L3 采集/脚本/分镜
    WF->>RW: 派发渲染任务
    RW->>API: Webhook 成片完成
    API->>WF: resumeHook
    WF->>GW: L6 RAG 质检
    WF->>API: L7 发布
```

---

## 4. 与市面工具差异

| 方案 | 问题 | 我们的选择 |
|------|------|-----------|
| 本地 Agent 编排 | 难多租户、难云部署 | Vercel Workflow |
| 直连厂商 API | 无 Failover/成本归因 | AI Gateway |
| FastAPI 扛渲染 | Functions 超时 | 控制面/渲染面分离 |
| 纯无代码工具 | 无法 C4D/定制分镜 | video-factory 可编程管线 |

核心竞争力：八层可观测、AI Gateway 多模型、Durable Workflow、专业渲染、一键 vercel deploy。

---

## 5. 商业化三层

### 产品层

| 套餐 | 月费 | 额度 | 模型 | 渲染 |
|------|------|------|------|------|
| Starter | 299 | 30条 | DeepSeek+Gemini | 标准模板 |
| Growth | 999 | 150条 | +Claude | +C4D 3D |
| Enterprise | 定制 | 无限 | BYOK | 专属节点 |

### 技术层成本：AI Gateway Token、Vercel 席位、Railway CPU、Blob 存储

### 交付层：15 分钟 onboarding、99.5% SLA、Enterprise 白标

---

## 6. 六周排期（Vercel-first）

| 周 | 任务 | 里程碑 |
|----|------|--------|
| W1 | Next.js 15 + Clerk + Postgres + shadcn | Dashboard 可部署登录 |
| W2 | AI SDK L1-L3 + v0.dev UI + Gateway tags | URL 出脚本+分镜 |
| W3 | Workflow L5 + KV 队列 + Hook 审批 | 编排跑通 Mock 渲染 |
| W4 | video-factory Railway + Webhook + Blob | 真实渲染一条视频 |
| W5 | pgvector RAG L6 + ai-koubo L7 + ECharts L8 | 八层 Production Ready |
| W6 | Preview per PR + 预算告警 + 安全审计 | Production 上线 |

---

## 7. 面试口述版（3 分钟）

开场：AI 电商种草视频 SaaS，商品链接到可发布短视频全链路自动化。

架构：控制面在 Vercel（Next.js 15、AI SDK、AI Gateway 统一路由），渲染面外部 Worker（video-factory、C4D），Webhook 回调。Vercel Workflow 持久编排，支持 use step 重试和 createHook 人工审批。

八层：L1 爬虫、L2 脚本、L3 分镜、L4 渲染、L5 Workflow、L6 RAG 质检、L7 发布、L8 看板。

差异：企业级 vercel deploy、多租户 RBAC、可编程 C4D 管线、Gateway 成本归因。

收尾：六周排期 W1 地基 W2 AI W3 Workflow W4 渲染 W5 质检发布 W6 上线；现有 Python orchestrator 八层适配器迁移为 Worker。

---

## 附录：风险与 KPI

| 风险 | 缓解 |
|------|------|
| Functions 超时 | 渲染面分离 + Workflow 等 Webhook |
| Gateway 预算超限 | 告警 + 402 降级 + 小模型兜底 |
| C4D 单点 | 队列削峰 + 多渲染节点 |

KPI：W6 成功率 85%、均时 30min、成本 2元/条；三月 95%、15min、1元/条。
"""

(ROOT / "PROJECT_PLAN.md").write_text(PROJECT_PLAN.strip() + "\n", encoding="utf-8")
print("PROJECT_PLAN written")
