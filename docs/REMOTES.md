# Git 远程仓库配置

> 开源依赖、独立仓 vs Monorepo 目录对照、版本迭代见 **[GIT_REPOS.md](GIT_REPOS.md)**。

本仓库采用与 [security-agent](https://github.com/23oyxw/security-agent) 相同的**双远程**模式：GitHub 为主（`origin`），Gitee 为镜像（`gitee`）。

## 当前远程

| 名称 | 用途 | URL |
|------|------|-----|
| `origin` | GitHub（主） | `git@github.com:23oyxw/ai-video-orchestrator.git` |
| `gitee` | Gitee（镜像） | `https://gitee.com/swok/ai-video-orchestrator.git` |

查看配置：

```bash
git remote -v
```

## 参考：security-agent 的远程模式

在 `C:\Users\oyxw\security-agent` 中（只读参考，勿与本项目混用）：

- `origin` → `git@github.com:23oyxw/security-agent.git`
- `gitee` → `https://gitee.com/swok/security-agent.git`

**切勿**将本仓库推送到 `security-agent` 的 URL。

## 首次创建远程仓库

远程仓库需为**空仓库**（不要勾选 README / .gitignore 初始化，避免无关提交）。

### GitHub（23oyxw/ai-video-orchestrator）

1. 登录 GitHub，或使用 CLI（需先 `gh auth login`）：

   ```bash
   gh repo create 23oyxw/ai-video-orchestrator --private --source=. --remote=origin --push=false
   ```

   若已手动添加 `origin`，可改为：

   ```bash
   gh repo create 23oyxw/ai-video-orchestrator --private
   ```

2. Web： [New repository](https://github.com/new) → Owner `23oyxw` → 名称 `ai-video-orchestrator` → 空仓库。

### Gitee（swok/ai-video-orchestrator）

1. 登录 [Gitee 新建仓库](https://gitee.com/projects/new)。
2. 所有者 `swok`，路径 `ai-video-orchestrator`，**不**初始化 README。

## 首次推送

在 `C:\Users\oyxw\Projects\ai-video-orchestrator` 且当前分支为 `main`（提交 `8cbb4cc` 或之后）：

```bash
git push -u origin main
git push -u gitee main
```

约定：

- **禁止** `git push --force` 到任一远程。
- **禁止**推送到 `23oyxw/security-agent` 或 `swok/security-agent`。

## 日常同步

推送到 GitHub 后同步 Gitee：

```bash
git push origin main
git push gitee main
```

若仅使用 HTTPS 访问 Gitee，可配置凭据或 SSH；与 security-agent 保持一致即可。

## 验证

```bash
git remote -v
git ls-remote origin
git ls-remote gitee
```

## 维护记录

- 2026-07-03：按 security-agent 双远程模式配置 `origin`（GitHub）与 `gitee`（Gitee）；远程空仓库需用户自行创建后首次推送。
