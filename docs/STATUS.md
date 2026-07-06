# 项目状态（2026-07-05）

## 完成度：**~92%**（Demo + RAG + L8 写入闭环）

| 区域 | 状态 | 说明 |
|------|------|------|
| L1–L8 编排 API | ✅ | FastAPI `:8765`，`scripts/test_api_protocol.ps1` |
| IntelliSafe-RAG | ✅ | `orchestrator/rag/`，stub + LlamaIndex 双轨 |
| L8 持久化 + 写入 | ✅ | SQLite/Postgres + 管线/Webhook/API 写入 |
| Dashboard（薄层） | ✅ | 管线 + 后台 API 两 Tab |
| Git 文档 | ✅ | [GIT_REPOS.md](GIT_REPOS.md) + [REMOTES.md](REMOTES.md) |
| v1.6 验证脚本 | ✅ | `npm run verify` / `npm run verify:rag` |
| Git 提交 | ⏸ | 需本机配置 `user.name` / `user.email` |
| 生产 Workflow | ⏸ | W3：Vercel Workflow 异步 L4+ |

## 版本对照（GIT_REPOS §五）

| 版本 | 状态 |
|------|------|
| v1.0 RAG 问答 | ✅ |
| v1.1 L8 数据库 | ✅ |
| v1.2 热点爬虫 | ✅ |
| v1.3 监控 + 报表 | ✅ |
| v1.4 八层 API + 前端 | ✅ |
| v1.6 验证脚本 | ✅ 本迭代 |
| v1.5 Clerk · v1.7 Vercel 生产 | ⏸ 待做 |

## 验证命令

```powershell
# 1. 启动后台
npm run dev:api

# 2. 仅 RAG + L8（快，~30s）
npm run verify:rag

# 3. 全量协议 + RAG（含 L1-L8 全管线，~3-5 min）
npm run verify

# 4. Python pytest（需 pip install -r requirements-dev.txt）
pytest tests/ -v
```

## Demo 流程（简化前端）

1. `npm run dev` 或分别 `dev:api` + `dev:web`
2. 打开 http://localhost:3000/dashboard
3. **管线** Tab：商品 URL → 运行
4. **后台 API** Tab：RAG / L8 JSON 调试

## 提交前（本机执行）

```powershell
git config user.name "Your Name"
git config user.email "you@example.com"
git add .
git commit -m "feat: IntelliSafe-RAG, L8 write pipeline, thin dashboard, GIT_REPOS docs"
git push origin main
git push gitee main
```
