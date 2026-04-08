# NotionSync

将 Notion 文档自动同步到 GitHub 仓库中。

## 功能简介

本仓库通过 GitHub Actions，定时（或手动）将 Notion Integration 所能访问的页面内容以 Markdown 格式同步到目标仓库的 `notion_export/` 目录中，并自动 commit & push。

支持同步**多个顶级页面**：在 Secret 中以逗号分隔多个页面 ID，脚本会自动递归导出每个页面及其全部子页面。
- 支持 Notion 图片 block 导出为 Markdown 图片语法。
- `column_list` 导出不会再生成“列1、列2”这类默认表头。

---

## 快速开始

### 1. 创建 Notion Integration

1. 打开 [Notion Integrations 页面](https://www.notion.so/my-integrations)，点击 **"+ New integration"**。
2. 填写名称（例如 "GitHub Repo"），选择关联的 Workspace，点击 **Submit**。
3. 复制 **"Internal Integration Secret"**（即 `NOTION_API_KEY`）。

### 2. 将 Integration 分享给目标页面（关键步骤）

> ⚠️ **未执行此步骤将导致同步时出现 404 Not Found 错误！**

1. 在 Notion 中打开你要同步的**每个顶级页面**。
2. 点击右上角 **"Share"**（分享）按钮。
3. 在 "Invite" 输入框中搜索你创建的 Integration 名称（如 "GitHub Repo"）。
4. 选中后点击 **"Invite"** 完成授权。
5. 子页面会自动继承父页面的权限，因此只需对每个顶级页面授权即可。

### 3. 获取页面 ID（NOTION_ROOT_PAGE_IDS）

从浏览器地址栏的 Notion 页面 URL 中提取：

```
https://www.notion.so/your-workspace/PageTitle-e4536863fdb049e38526a681651d8776
                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                               这 32 位十六进制字符串就是 Page ID
```

- **无横线格式**（32位）：`e4536863fdb049e38526a681651d8776`
- **UUID 格式**（带横线）：`e4536863-fdb0-49e3-8526-a681651d8776`

两种格式填入 Secret 均可，脚本会自动识别。若 URL 末尾没有 `-xxxxx` 结尾的长字符串，请尝试点击页面右上角 `...` → "Copy link" 再提取。

**多个页面**：将多个 ID 用英文逗号分隔填入同一个 Secret，例如：

```
e4536863fdb049e38526a681651d8776,abcd1234efgh5678ijkl9012mnop3456
```

### 4. 配置 GitHub Secrets

进入本仓库 **Settings → Secrets and variables → Actions**，新建如下 Secret：

| Secret 名称              | 说明                                                                                  |
|--------------------------|--------------------------------------------------------------------------------------|
| `NOTION_API_KEY`         | 你在第 1 步获得的 Notion Integration Secret                                            |
| `NOTION_ROOT_PAGE_IDS`   | 要同步的顶级页面 ID，多个页面用英文逗号分隔（有无横线均可，见第 3 步）                      |
| `TARGET_REPO`            | 目标私有仓库，格式：`owner/repo`（例如 `yourname/notion-docs`）                          |
| `TARGET_PAT`             | 有目标仓库写权限的 GitHub Personal Access Token（经典 PAT，勾选 `repo`）                 |
| `TARGET_BRANCH`          | 目标仓库的分支名（例如 `main`）                                                          |

> **兼容旧版**：若你已配置了 `NOTION_ROOT_PAGE_ID`（单页面，旧版 Secret 名称），脚本同样支持，无需修改。建议迁移到 `NOTION_ROOT_PAGE_IDS` 以启用多页面同步。

### 5. 触发同步

- **自动触发**：每小时自动运行一次。
- **手动触发**：进入仓库 **Actions** → 选择 **"Sync Notion to Private Docs Repo"** → 点击 **"Run workflow"**。

同步完成后，Notion 页面内容会以 Markdown 格式保存到目标仓库的 `notion_export/` 目录中，按页面层级嵌套成目录树。

---

## 主要文件说明

| 文件/目录 | 说明 |
|-----------|------|
| `scripts/notion_sync.py` | 主同步脚本，递归拉取 Notion 页面并写入本地 |
| `.github/workflows/notion-sync.yml` | GitHub Actions 工作流配置 |
| `notion_export/` | 同步输出目录（在目标仓库中由脚本自动创建） |

---

## 常见问题

**Q: Action 报错 `404 Not Found` / `Could not find page with ID`？**  
A: 这是最常见的问题，通常由以下原因之一引起：
1. **页面未分享给 Integration**：在 Notion 打开顶级页面 → 右上角 "Share" → "Invite" → 搜索你的 Integration 并授权。
2. **NOTION_ROOT_PAGE_IDS 填写有误**：请从 Notion 页面 URL 末尾重新提取 32 位十六进制 ID（见"快速开始"第 3 步）。
3. **Integration token 与 workspace 不匹配**：确保 `NOTION_API_KEY` 对应的 Integration 与目标页面在同一个 Notion workspace。

脚本启动时会自动检测 token 有效性，并在日志中给出具体的修复步骤。单个不可访问的页面会打印警告并跳过，不影响其余页面的同步。

**Q: Action 提示找不到脚本文件？**  
A: 请确保 `scripts/notion_sync.py` 已经提交到仓库，且 workflow 中的 `run` 命令引用的路径与文件名完全一致。

**Q: 同步后没有新文件？**  
A: 请检查你的 Notion Integration 是否已被 Share 到目标页面。未授权的页面无法通过 API 访问。

**Q: Push 权限不足 / 403 错误？**  
A: 请检查仓库的 Actions 权限设置：**Settings → Actions → General → Workflow permissions**，确保已开启 **"Read and write permissions"**。另外确认 `TARGET_PAT` 已勾选 `repo` 权限且对目标仓库有写权限。
