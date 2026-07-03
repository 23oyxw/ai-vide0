# API 协议规范（FastAPI Orchestrator）

> 编排器默认地址：`http://127.0.0.1:8765`  
> 控制面 Web 代理：`apps/web` → `/api/pipeline/run`、`/api/status`

## 1. 统一响应信封

所有 Orchestrator 接口（含 `/health`、`/tools/check`）均返回同一 JSON 结构：

```json
{
  "ok": true,
  "data": { },
  "error": null,
  "meta": {
    "layer": "L5",
    "job_id": "a1b2c3d4",
    "timestamp": "2026-07-03T12:00:00.000000+00:00"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 业务是否成功 |
| `data` | object \| null | 成功时的载荷 |
| `error` | object \| null | 失败时 `{ code, message, detail? }` |
| `meta.layer` | string \| null | 所属层（L0=系统，L1–L8=业务层） |
| `meta.job_id` | string \| null | 关联任务 ID（如有） |
| `meta.timestamp` | string | UTC ISO8601 时间戳 |

HTTP 4xx/5xx 时仍返回信封，`ok=false`，`error` 非空。

---

## 2. 端点清单

| 方法 | 路径 | 层 | 说明 |
|------|------|-----|------|
| GET | `/health` | L0 | 服务健康 |
| GET | `/tools/check` | L0 | 外部工具探测 |
| GET | `/layers` | L0 | 八层注册表 |
| GET | `/agent/crawler` | L1 | 选品爬虫（GET） |
| POST | `/agent/crawler` | L1 | 选品爬虫 |
| POST | `/monitor` | L6 | 质检监控（POST） |
| GET | `/monitor` | L6 | 质检监控（GET） |
| GET/POST | `/data/click` | L8 | 点击归因 |
| GET/POST | `/data/conversion` | L8 | 转化数据 |
| GET/POST | `/data/order` | L8 | 订单/GMV |
| GET/POST | `/data/analysis` | L8 | 分析与优化建议 |
| POST | `/pipeline/run` | L5 | 八层管线编排 |
| POST | `/tools/video-factory/run` | L4 | 工具：video-factory |
| POST | `/tools/c4d/render` | L4 | 工具：C4D 渲染 |

### Web 控制面代理

| 方法 | 路径 | 上游 |
|------|------|------|
| POST | `/api/pipeline/run` | `POST /pipeline/run` |
| GET | `/api/status` | `GET /health` + 本地 Gateway 状态 |
| POST | `/api/chat` | Vercel AI Gateway（独立协议） |

---

## 3. 接口详情与示例

### 3.1 GET `/health`

**响应示例：**

```json
{
  "ok": true,
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "layers": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
  },
  "error": null,
  "meta": { "layer": "L0", "job_id": null, "timestamp": "..." }
}
```

---

### 3.2 POST `/agent/crawler`（L1）

**请求：**

```json
{
  "product_url": "https://example.com/product/demo",
  "competitor_urls": ["https://example.com/competitor/1"],
  "job_id": "optional-custom-id"
}
```

**响应 `data`：**

```json
{
  "crawled_url": "https://example.com/product/demo",
  "selection_card": {
    "title": "Demo 选品卡片",
    "pain_points": ["痛点 A：功效不明显", "痛点 B：价格敏感"],
    "category": "beauty"
  },
  "competitor_count": 1,
  "rag_candidates": ["rag_candidate_a1b2c3d4"]
}
```

---

### 3.3 POST `/monitor`（L6）

**请求：**

```json
{
  "job_id": "a1b2c3d4",
  "video_url": "https://blob.example/video.mp4",
  "script_text": "15 秒种草脚本..."
}
```

**响应 `data`：**

```json
{
  "qa_score_avg": 0.85,
  "active_jobs": 0,
  "checks": [
    { "name": "visual_quality", "passed": true, "score": 0.88, "message": "画面清晰度 stub 通过" },
    { "name": "script_intellisafe", "passed": true, "score": 0.90, "message": "脚本合规 stub 通过" },
    { "name": "structure_15s", "passed": true, "score": 0.82, "message": "15 秒结构 stub 通过" }
  ],
  "message": "RAG/QA monitor stub — connect Qdrant for full RAG"
}
```

GET `/monitor?job_id=xxx` 返回相同结构。

---

### 3.4 L8 数据接口

#### GET/POST `/data/click`

POST 请求体（均可选）：

```json
{ "job_id": "a1b2c3d4", "utm_campaign": "seed_video", "start_date": "2026-07-01", "end_date": "2026-07-03" }
```

响应 `data`：

```json
{
  "clicks": 1280,
  "unique_clicks": 960,
  "ctr": 0.042,
  "records": [{ "job_id": "a1b2c3d4", "utm_campaign": "seed_video", "clicks": 1280 }]
}
```

#### GET/POST `/data/conversion`

```json
{ "conversions": 86, "conversion_rate": 0.089, "records": [{ "job_id": "demo", "conversions": 86 }] }
```

#### GET/POST `/data/order`

```json
{ "orders": 42, "gmv": 12880.5, "records": [{ "job_id": "demo", "orders": 42, "gmv": 12880.5 }] }
```

#### GET/POST `/data/analysis`

POST 请求：

```json
{ "job_id": "a1b2c3d4", "metrics": { "ctr": 0.042, "cvr": 0.089 } }
```

响应 `data`：

```json
{
  "summary": "L8 分析 stub：基于提交 metrics 生成优化建议",
  "optimization_hints": [
    "提高前3秒 hook 强度 -> 反馈 L2 脚本模板",
    "L3: 增加产品特写镜头占比"
  ],
  "feedback_targets": ["L1", "L2", "L3"]
}
```

---

### 3.5 POST `/pipeline/run`（L5）

**请求：**

```json
{
  "product_url": "https://example.com/product/demo",
  "demo_name": "product_ad",
  "c4d_project": null,
  "layers": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
  "force_qa_fail": false
}
```

**响应 `data`：**

```json
{
  "job_id": "f3e2a1b0",
  "status": "ok",
  "pipeline_state": "analyzed",
  "layers": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
  "layer_results": [
    { "layer_id": "L1", "status": "ok", "message": "stub crawl: ...", "artifacts": { "crawled_url": "..." } }
  ],
  "artifacts": { "crawled_url": "...", "optimization_hints": "..." },
  "errors": [],
  "retry_from": null,
  "optimization_hints": ["提高前3秒 hook 强度 -> 反馈 L2 脚本模板"]
}
```

| `status` | 含义 |
|----------|------|
| `ok` | 管线成功 |
| `qa_failed` | L6 质检未通过，`retry_from` 通常为 `L2` |
| `error` | 某层执行失败 |

---

### 3.6 GET `/tools/check`

返回 video-factory、ai-koubo、C4D、FFmpeg、OpenClaw 探测结果，包在 `data` 内。

---

## 4. 错误示例

层顺序违规（POST `/pipeline/run`，layers 乱序）：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "http_400",
    "message": "Layer order violation at L3: must follow L1->L8 DAG",
    "detail": "Layer order violation at L3: must follow L1->L8 DAG"
  },
  "meta": { "layer": null, "job_id": null, "timestamp": "..." }
}
```

---

## 5. 本地测试

```powershell
# 启动编排器
cd C:\Users\oyxw\Projects\ai-video-orchestrator
.\.venv\Scripts\python.exe -m uvicorn orchestrator.main:app --host 127.0.0.1 --port 8765

# 另开终端运行协议测试
.\scripts\test_api_protocol.ps1
```

可选环境变量：`$env:ORCHESTRATOR_URL = "http://127.0.0.1:8765"`

---

## 6. 与 MASTER_PLAN 对照

| MASTER_PLAN 附录 | 本仓库 FastAPI 实现 |
|------------------|---------------------|
| `/agent/crawler` | ✅ POST |
| `/monitor` | ✅ GET + POST |
| `/data/click` `/data/conversion` `/data/order` | ✅ GET + POST stub |
| `/data/analysis` | ✅ GET + POST stub |
| `/pipeline/run` | ✅ POST（统一信封） |
| `/health` `/tools/check` | ✅ GET（统一信封） |

生产目标路径（Vercel `/api/content/generate` 等）见 `docs/MASTER_PLAN.md` 附录 15.1，由 Workflow 实现；本仓库 FastAPI 为本地 Demo 与 MCP 联调入口。
