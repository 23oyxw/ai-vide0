# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SECTIONS_PATH = Path(__file__).resolve().parent / "master_sections.json"

CROSS_REF = (
    "> **文档索引**：本文件为分册说明；**唯一总览**见 [MASTER_PLAN.md](./MASTER_PLAN.md)"
    "（八层架构、排期、商业化与 API 清单）。\n\n"
)


def write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8", newline="\n")


def build_master_plan(sections: dict[str, str]) -> str:
    order = [f"s{i}" for i in range(1, 16)]
    body = "\n\n".join(sections[k].strip() for k in order if k in sections)
    header = sections.get("header", "").strip()
    return header + "\n\n" + body + "\n"


def ensure_cross_ref(text: str) -> str:
    head = "\n".join(text.splitlines()[:14])
    if "文档索引" in head and "MASTER_PLAN.md" in head:
        return text
    lines = text.splitlines()
    if not lines:
        return CROSS_REF + text
    out: list[str] = [lines[0]]
    i = 1
    while i < len(lines) and lines[i].startswith(">"):
        out.append(lines[i])
        i += 1
    if i < len(lines) and lines[i].strip() == "":
        out.append(lines[i])
        i += 1
    out.extend(["", CROSS_REF.strip(), *lines[i:]])
    return "\n".join(out) + "\n"


README = """# AI Video Orchestrator

**多模态 AI 种草视频一站式 SaaS** — 本仓库为八层工具统筹与本地 Demo（FastAPI + MCP）。

> 完整愿景、架构、排期、商业化与 API 清单见 **[docs/MASTER_PLAN.md](docs/MASTER_PLAN.md)**。

## 快速开始（本地 Demo）

```powershell
cd C:\\Users\\oyxw\\Projects\\ai-video-orchestrator
copy .env.example .env
.\\scripts\\setup-tools.ps1
python -m venv .venv
.\\.venv\\Scripts\\pip install -r requirements.txt
.\\.venv\\Scripts\\uvicorn orchestrator.main:app --reload --port 8765
```

或：` .\\scripts\\run-demo.ps1`

## 文档

| 文档 | 说明 |
|------|------|
| [MASTER_PLAN.md](docs/MASTER_PLAN.md) | **主文档（中文）** |
| [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | 执行摘要 |
| [TECH_STACK.md](docs/TECH_STACK.md) | 技术栈 |
| [DEPLOY.md](docs/DEPLOY.md) | Vercel 部署 |
| [TOOLING.md](docs/TOOLING.md) | 工具统筹 |

## 环境变量

`VIDEO_FACTORY_PATH`、`AI_KOUBO_PATH`、`C4D_ROOT`、`FFMPEG_PATH`

可选：`docker compose up -d`
"""

PROJECT_PLAN = """# AI 种草视频 SaaS — 项目计划（执行摘要）

> **完整主文档**：[MASTER_PLAN.md](./MASTER_PLAN.md)（八层架构、技术总图、11 步链路、6 周排期、API 附录）
> **版本**：v3.0 · **原则**：控制面 Vercel-first，渲染面外置 Worker

---

## 定位

为中小商家与 MCN 提供 **「输入商品链接 → 输出多平台种草视频」** 的全链路 SaaS：选品（L1）、脚本（L2）、分镜（L3）、渲染（L4）、编排（L5）、质检（L6）、发布（L7）、数据闭环（L8）。

## 架构一句话

- **Vercel**：Next.js 15、AI SDK、AI Gateway、Workflow、Postgres、KV、Blob、Clerk
- **Worker / 本机**：video-factory、即梦/Seedance/ComfyUI、C4D（`C:\\BKC4D`）、AE（待装）、FFmpeg
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
"""


def main() -> list[Path]:
    sections = json.loads(SECTIONS_PATH.read_text(encoding="utf-8"))
    touched: list[Path] = []
    mp = build_master_plan(sections)
    write_utf8(DOCS / "MASTER_PLAN.md", mp)
    touched.append(DOCS / "MASTER_PLAN.md")
    write_utf8(ROOT / "README.md", README)
    touched.append(ROOT / "README.md")
    write_utf8(DOCS / "PROJECT_PLAN.md", PROJECT_PLAN)
    touched.append(DOCS / "PROJECT_PLAN.md")
    for name in ("TECH_STACK.md", "DEPLOY.md", "TOOLING.md"):
        path = DOCS / name
        if path.exists():
            text = ensure_cross_ref(path.read_text(encoding="utf-8"))
        else:
            text = CROSS_REF + f"# {name[:-3]}\n\n（待补充）\n"
        write_utf8(path, text)
        touched.append(path)
    return touched


if __name__ == "__main__":
    for p in main():
        print(f"Wrote {p.relative_to(ROOT)} ({len(p.read_text(encoding='utf-8').splitlines())} lines)")