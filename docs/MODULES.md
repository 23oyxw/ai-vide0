# 八模块架构说明

> 版本 v1.0 - orchestrator/modules/ 独立包

## 模块 vs 管线

- **模块**: 可独立 HTTP 调用的业务能力包 (service/router/models)
- **管线**: `/pipeline/run` 内部调用各模块 service，按 L1-L8 串联

## 八个模块

| 模块 | 路径 | API |
|------|------|-----|
| M1 热点检索 | /modules/l1-crawler | POST /search, GET /topics |
| M2 内容创作 | /modules/l2-content | POST /generate-script, GET /scripts/{id} |
| M3 镜头重构 | /modules/l3-storyboard | POST /build-from-script, GET /storyboard/{id} |
| M4 渲染合成 | /modules/l4-render | POST /render, GET /render/{job_id}/status |
| M5 调度中枢 | /modules/l5-scheduler | GET/POST /jobs, POST /jobs/{id}/retry |
| M6 质检闭环 | /modules/l6-qa | POST /validate, GET /rules |
| M7 发布输出 | /modules/l7-publish | POST /publish, GET /published |
| M8 数据运营 | /modules/l8-analytics | GET /dashboard, /click, /conversion, /order, /analysis |

Dashboard 8 个 Tab 通过 /api/modules/* 直接调用模块 API。
完整演示仍用 POST /pipeline/run。
