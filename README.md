# Notion-Sync

将 Notion 文档自动同步到 GitHub 仓库中。

## 功能简介

本仓库通过 GitHub Actions，定时（或手动）将 Notion Integration 所能访问的页面内容以 Markdown 格式同步到当前仓库的 `notion_pages/` 目录中，并自动 commit & push。

---

## 快速开始

### 1. 创建 Notion Integration

1. 打开 [Notion Integrations 页面](https://www.notion.so/my-integrations)，点击 **"+ New integration"**。
2. 填写名称，选择关联的 Workspace，点击 **Submit**。
3. 复制 **"Internal Integration Secret"**（即 `NOTION_API_KEY`）。
4. 在 Notion 中，打开要同步的页面，右上角 **"Share"** → **"Invite"** 你创建的 Integration。

### 2. 配置 GitHub Secrets

进入本仓库 **Settings → Secrets and variables → Actions**，新建如下 Secret：

| Secret 名称        | 说明                                      |
|--------------------|-------------------------------------------|
| `NOTION_API_KEY`   | 你在第 1 步获得的 Notion Integration Secret |

### 3. 触发同步

- **自动触发**：每天 UTC 00:00 自动运行。
- **手动触发**：进入仓库 **Actions** → 选择 **"Notion to GitHub Sync"** → 点击 **"Run workflow"**。

同步完成后，Notion 页面内容会以 Markdown 格式保存到仓库的 `notion_pages/` 目录中。

---

## 主要文件说明

| 文件/目录 | 说明 |
|-----------|------|
| `scripts/notion_sync.py` | 主同步脚本，负责拉取 Notion 页面并写入本地 |
| `.github/workflows/notion-sync.yml` | GitHub Actions 工作流配置 |
| `notion_pages/` | 同步输出目录（由脚本自动创建） |

---

## 常见问题

**Q: Action 提示找不到脚本文件？**  
A: 请确保 `scripts/notion_sync.py` 已经提交到仓库，且 workflow 中的 `run` 命令引用的路径与文件名完全一致。

**Q: 同步后没有新文件？**  
A: 请检查你的 Notion Integration 是否已被 Share 到目标页面。未授权的页面无法通过 API 访问。

**Q: Push 权限不足 / 403 错误？**  
A: 请检查仓库的 Actions 权限设置：**Settings → Actions → General → Workflow permissions**，确保已开启 **"Read and write permissions"**。

