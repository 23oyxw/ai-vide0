# AI 种草视频 SaaS — 项目计划（执行摘要）

> **完整主文档**：[MASTER_PLAN.md](./MASTER_PLAN.md)（八层架构、技术总图、11 步链路、6 周排期、API 附录）
> **版本**：v3.0 · **原则**：控制面 Vercel-first，渲染面外置 Worker

---

## 定位

为中小商家与 MCN 提供 **「输入商品链接 → 输出多平台种草视频」** 的全链路 SaaS：选品（L1）、脚本（L2）、分镜（L3）、渲染（L4）、编排（L5）、质检（L6）、发布（L7）、数据闭环（L8）。

## 架构一句话

- **Vercel**：Next.js 15、AI SDK、AI Gateway、Workflow、Postgres、KV、Blob、Clerk
- **Worker / 本机**：video-factory、即梦/Seedance/ComfyUI、C4D（`C:\BKC4D`）、AE（待装）、FFmpeg
- **集成**：ai-koubo-platform（L2/L7）；**不以 OpenClaw 为生产核心**

## 6 周里程碑（摘要）

| 周 | 交付 |
|----|------|
| W1 | Next.js + Clerk + Postgres + Dashboard |
| W2 | L1–L3 + Gateway + ai-koubo |
| W3 | Workflow + video-factory + Webhook |
| W4 | RAG + L6/L7 + Blob 发布 |
| W5 | L8 看板 + 爆款逆向 MVP |
| W6 | 端到端 Demo + Preview 上线 |

## 商业化（摘要）

免费体验 · 会员（数据看板 + 爆款模板）· 定制（C4D 管线 + 专属 RAG）

## 下一步阅读

- 技术选型 → [TECH_STACK.md](./TECH_STACK.md)
- 部署 → [DEPLOY.md](./DEPLOY.md)
- Cursor MCP 与仓库映射 → [TOOLING.md](./TOOLING.md)
