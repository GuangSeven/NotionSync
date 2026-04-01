# Notion-Sync

本仓库是 **Notion 文档自动同步的代码仓库**，仅存放同步脚本和 GitHub Actions 工作流配置。  
生成的 Markdown 文档产物**不会**保存在本仓库，而是自动推送到你指定的**私有目标仓库**中。

---

## 目录

- [仓库定位](#仓库定位)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
  - [第一步：创建 Notion Integration](#第一步创建-notion-integration)
  - [第二步：准备目标私有仓库](#第二步准备目标私有仓库)
  - [第三步：生成 GitHub PAT](#第三步生成-github-pat)
  - [第四步：配置 Secrets](#第四步配置-secrets)
  - [第五步：手动触发同步](#第五步手动触发同步)
- [Secrets 配置说明](#secrets-配置说明)
- [工作流主要流程](#工作流主要流程)
- [常见问题](#常见问题)
- [相关链接](#相关链接)

---

## 仓库定位

| 仓库 | 作用 |
|------|------|
| **本仓库（Notion-Sync）** | 存放同步脚本 `scripts/notion_sync.py` 和 Actions 工作流配置，不存放任何文档文件 |
| **目标私有仓库** | 接收从 Notion 导出的 Markdown 文档产物，由 `TARGET_REPO` Secret 指定 |

---

## 功能特性

- **层级目录结构保持**：脚本按照 Notion 的父子页面关系递归导出，每个页面生成同名目录，页面内容写入该目录下的 `index.md`，完整保留原始文档层级。
- **自动定时同步**：默认每小时自动运行一次，也可以在 Actions 页面随时手动触发。
- **推送到独立私有仓库**：文档产物与代码完全隔离，推送到你指定的私有文档仓库，不污染本代码仓库。
- **支持多种 Notion 块类型**：段落、各级标题、列表、待办、引用、代码块、分隔线等。

---

## 快速开始

### 第一步：创建 Notion Integration

1. 访问 [Notion Integrations 页面](https://www.notion.so/my-integrations)，点击 **New integration**。
2. 填写名称（如 `GitHub Sync`），选择关联的 Workspace，点击 **Submit**。
3. 复制页面中 **Internal Integration Token**（即 `NOTION_API_KEY`）。
4. 打开你想要同步的 Notion 根页面，点击右上角 **...** → **Add connections**，找到并授权你刚创建的 Integration。  
   > ⚠️ 只有授权了 Integration 的页面（及其子页面）才能被脚本读取。

### 第二步：准备目标私有仓库

在 GitHub 创建（或使用已有的）私有仓库，用来存放从 Notion 导出的文档，例如：`your-username/my-notion-docs`。  
该仓库可以是空的，脚本会自动在其中创建 `notion_export/` 目录。

### 第三步：生成 GitHub PAT

脚本需要一个有目标私有仓库写权限的 Personal Access Token（PAT）才能推送文档产物。

1. 登录 GitHub，点击右上角头像 → **Settings**。
2. 滚动到底部，点击 **Developer settings** → **Personal access tokens** → **Tokens (classic)**。
3. 点击 **Generate new token (classic)**，填写描述（如 `Notion Sync Bot`），选择有效期。
4. 在权限列表中勾选 **`repo`**（包含私有仓库的读写权限），其他权限无需勾选。
5. 点击 **Generate token**，**立即复制**生成的 Token（页面刷新后将无法再次查看）。

### 第四步：配置 Secrets

进入 **本代码仓库（Notion-Sync）** → **Settings** → **Secrets and variables** → **Actions**，添加以下 5 个 Repository Secret：

| Secret 名称 | 说明 | 示例值 |
|---|---|---|
| `NOTION_API_KEY` | Notion Integration Token | `secret_xxxxxxxxxxxxxxxx` |
| `NOTION_ROOT_PAGE_ID` | 要同步的 Notion 根页面 ID（从页面 URL 末尾获取，32 位十六进制串） | `e4536863fdb049e38526a681651d8776` |
| `TARGET_REPO` | 目标私有文档仓库（`owner/repo` 格式） | `your-username/my-notion-docs` |
| `TARGET_BRANCH` | 目标仓库的目标分支名 | `main` |
| `TARGET_PAT` | 第三步生成的 GitHub PAT（需有目标仓库写权限） | `ghp_xxxxxxxxxxxxxxxx` |

> **如何获取页面 ID？**  
> 打开 Notion 页面，复制浏览器地址栏中的 URL，最后一段（去掉连字符的 32 位字符串）即为页面 ID。  
> 例如：`https://www.notion.so/tblog/e4536863fdb049e38526a681651d8776` → ID 为 `e4536863fdb049e38526a681651d8776`

### 第五步：手动触发同步

1. 进入本仓库 GitHub 页面，点击顶部 **Actions** 标签。
2. 在左侧列表中找到 **Sync Notion to Private Docs Repo** 工作流，点击进入。
3. 点击右侧 **Run workflow** 按钮，在弹出窗口中点击绿色 **Run workflow** 确认。
4. 刷新页面，可以看到一条新的运行记录，点进去实时查看日志。

---

## Secrets 配置说明

```
Notion-Sync（代码仓库）
└── Settings
    └── Secrets and variables
        └── Actions
            ├── NOTION_API_KEY        # Notion API 密钥
            ├── NOTION_ROOT_PAGE_ID   # Notion 根页面 ID
            ├── TARGET_REPO           # 目标文档仓库（owner/repo）
            ├── TARGET_BRANCH         # 目标分支（如 main）
            └── TARGET_PAT            # 有目标仓库写权限的 GitHub PAT
```

---

## 工作流主要流程

```
┌─────────────────────────────────────────────────────┐
│              GitHub Actions 工作流                   │
│                                                     │
│  1. Checkout 代码仓库（获取 notion_sync.py 脚本）     │
│  2. Checkout 目标私有文档仓库（用 TARGET_PAT 鉴权）   │
│  3. 运行 scripts/notion_sync.py                     │
│     └─ 按 Notion 父子页面层级递归导出 Markdown 文件  │
│        到 target/notion_export/ 目录                 │
│  4. git commit + git push 推送到目标私有仓库          │
└─────────────────────────────────────────────────────┘
```

导出后目标仓库结构示例：

```
my-notion-docs/
└── notion_export/
    └── 知识管理/
        ├── index.md          # 「知识管理」页面内容
        ├── 项目规划/
        │   ├── index.md
        │   └── Q1 计划/
        │       └── index.md
        └── 读书笔记/
            └── index.md
```

---

## 常见问题

### ❶ Actions 报错：`403` 或 `Permission denied`（推送目标仓库失败）

- 检查 `TARGET_PAT` 是否有目标私有仓库的 `repo` 写权限。
- 确认 `TARGET_REPO` 填写格式正确（`owner/repo`，不带 `https://github.com/`）。
- PAT 是否已过期？过期后需重新生成并更新 Secret。

### ❷ 脚本报错：`Could not find page` 或拉不到任何 Notion 内容

- 确认已在 Notion 页面右上角 **...** → **Add connections** 中授权了你的 Integration。
- 授权必须在根页面上操作，子页面会自动继承权限。
- 确认 `NOTION_ROOT_PAGE_ID` 填写的是正确的页面 ID（32 位十六进制，无连字符）。

### ❸ 如何手动触发 Actions 工作流？

进入 **Actions** → 选择 **Sync Notion to Private Docs Repo** → 点击右侧 **Run workflow** 按钮即可立即触发一次同步，无需等待定时任务。

### ❹ 如何修改同步频率？

编辑 `.github/workflows/notion-sync.yml` 中 `schedule.cron` 字段，使用标准 [cron 表达式](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)。当前默认为每小时同步一次（`0 * * * *`）。

### ❺ 是否支持数据库页面？

当前脚本按 `child_page` 类型递归导出，Notion Database 作为独立块类型暂不支持导出数据库内容，后续可扩展。

---

## 相关链接

- [Notion API 官方文档](https://developers.notion.com/)
- [Notion Integration 创建指南](https://developers.notion.com/docs/create-a-notion-integration)
- [notion-client Python SDK](https://github.com/ramnes/notion-sdk-py)
- [GitHub Actions 定时触发（schedule）](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [GitHub Personal Access Tokens 文档](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
