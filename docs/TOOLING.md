> ⚠️ **完整工具与架构说明见 [MASTER_PLAN.md](./MASTER_PLAN.md) 第 6 节**。本文保留本地工具链操作细节.


> **文档索引**：本文件为分册说明；**唯一总览**见 [MASTER_PLAN.md](./MASTER_PLAN.md)（八层架构、排期、商业化与 API 清单）。
# AI 种草视频 SaaS — 工具统筹方案

> 面试可用：本文只讲**工具层**，不涉及完整业务逻辑。目标是把 8 层架构映射到**可复用、可编排**的具体工具链。

## 一、总体思路

```
IDE/Agent 层: Cursor MCP | Cline MCP | OpenClaw Agent | Continue
                    │ MCP / HTTP
编排器: ai-video-orchestrator (FastAPI) — Layer Registry + Adapters
                    │
    video-factory | ai-koubo | C4D MCP | OpenClaw CLI
```

**核心原则：**
1. 一套编排器 — orchestrator/ FastAPI 统一调度
2. 多入口同一后端 — Cursor/Cline/OpenClaw 共用 MCP
3. 本地优先 — 不依赖 Docker 即可跑 Demo
4. 环境变量串联现有项目

## 二、8 层 → 工具映射

| 层级 | 职责 | 工具/组件 | 本仓库位置 |
|------|------|-----------|------------|
| L1 爬虫 | 商品/竞品数据采集 | Python + fetch MCP | layers/l1_crawler.py |
| L2 内容 | 文案/脚本生成 | DeepSeek via ai-koubo / Cline | layers/l2_content.py |
| L3 分镜 | 分镜 YAML | video-factory demos/*.yaml | layers/l3_storyboard.py |
| L4 渲染 | 视频合成/3D 渲染 | video-factory + C4D MCP + OpenClaw | layers/l4_render.py |
| L5 调度 | 任务编排/队列 | orchestrator FastAPI + OpenClaw Agent | layers/l5_scheduler.py |
| L6 质检 | QA/合规 | RAG stub + /monitor | layers/l6_qa.py |
| L7 发布 | 多平台分发 | ai-koubo publish provider | layers/l7_publish.py |
| L8 数据 | 指标/看板 | MySQL + ECharts stub | layers/l8_data.py |

## 三、环境变量

| 变量 | 默认路径 | 用途 |
|------|----------|------|
| VIDEO_FACTORY_PATH | C:\Users\oyxw\Projects\video-factory | L3/L4 |
| AI_KOUBO_PATH | C:\Users\oyxw\Projects\ai-koubo-platform | L2/L7 |
| C4D_ROOT | C:\BKC4D | L4 3D 渲染 |
| FFMPEG_PATH | C:\Users\oyxw\bin\ffmpeg\ffmpeg.exe | 音视频 |

> 视频后期分工（粗剪/ C4D Hero / AE 合成 / 终混）见 [POST_PRODUCTION_LOGIC.md](./POST_PRODUCTION_LOGIC.md)。

## 四、MCP 接入

C4D MCP: mcp/c4d-mcp/server.py
- c4d_render_project — Commandline.exe 无头渲染
- c4d_check_installation — 检查安装
- c4d_list_resources — 浏览 .c4d 工程

Cursor: 合并 config/cursor-mcp.json 到 MCP 设置
Cline: 使用 config/cline-mcp-snippet.json
OpenClaw: bash config/openclaw-mcp.sh

## 五、编排器 API

GET /health — 健康检查
GET /tools/check — 验证工具路径
POST /pipeline/run — 执行流水线
GET /monitor — L6 QA 监控 stub

## 六、本地 Demo

.\scripts\setup-tools.ps1
.\scripts\run-demo.ps1

## 七、面试话术

Q: 8层工具怎么统一？
A: FastAPI 编排器 + Layer Registry，每层 adapter 封装外部项目；IDE 通过 MCP 暴露同一工具面。

Q: Cursor 和 OpenClaw 怎么共用 C4D？
A: 独立 FastMCP server，三端配置同一 server.py，C4D_ROOT 一致。

Q: 没有 Docker 能跑吗？
A: 可以。编排器纯 Python；Docker 只服务 L6 RAG / L8 持久化。
