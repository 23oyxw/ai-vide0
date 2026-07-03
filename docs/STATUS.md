# 项目状态（2026-07-04）

## 已完成（已暂存，待提交）

- L3–L8 中间层端到端接线：storyboard、video-factory、job store JSON、manifest QA、L7 ai-koubo、L8 optimization hints
- 新增 `orchestrator/job_store.py`、`orchestrator/adapters/storyboard.py`、`orchestrator/adapters/c4d_scene2.py`
- 集成测试脚本 `scripts/test_full_pipeline.ps1`、扩展 `scripts/test_api_protocol.ps1`
- **修复**：`orchestrator/layers/l4_render.py` 空字节损坏（导致 uvicorn 无法启动）

## 测试结果（本机 :8765）

| 脚本 | 结果 |
|------|------|
| `scripts/test_api_protocol.ps1` | **19/19 PASS** |
| `scripts/test_full_pipeline.ps1` | **PASS**（L1–L8 全绿，qa_score=1.0） |

## 提交阻塞

Git 未配置 `user.name` / `user.email`，无法执行 commit（按规则不可运行 `git config`）。

**提交前请在本机执行：**

```powershell
git config user.name "Your Name"
git config user.email "you@example.com"
git add orchestrator/layers/l4_render.py   # 含空字节修复
git commit -m "Wire L3-L8 pipeline layers with integration tests"
```

## 产品方向

Web 控制台 + API + 小程序（非原生 App）。详见 `docs/MASTER_PLAN.md`。

## 建议下一步

1. 配置 git 身份并提交暂存变更
2. 与兴图确认「双源」边界 → `docs/CLIENT_XINGTU.md`
3. W3：Vercel Workflow 异步触发 L4+（当前 L1–L8 为同步 HTTP）
