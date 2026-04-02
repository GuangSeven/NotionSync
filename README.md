# Notion-Sync

> **本仓库是「代码仓库」**，只存放同步脚本和 GitHub Actions 工作流，**不存放**导出的 Notion 文档。  
> 文档将被推送到你指定的**私有目标仓库**（`TARGET_REPO`）。

---

## 工作原理

```
触发 workflow
    │
    ├─ 检出本仓库（代码）
    ├─ 检出目标私有仓库（文档）
    ├─ 运行 scripts/notion_sync.py
    │       从 NOTION_ROOT_PAGE_ID 开始递归导出
    │       保留父子层级（子页面 → 子目录）
    │       输出 Markdown 文件写入目标仓库工作区
    └─ 提交并 push 到 TARGET_REPO / TARGET_BRANCH
```

本仓库在整个流程中**只需读取权限**，向目标仓库的写入操作通过 `TARGET_PAT` 完成，遵循最小权限原则。

---

## 快速开始

### 1. Fork / Clone 本仓库

将本仓库 Fork 到你的 GitHub 账号（或直接使用），无需修改代码。

### 2. 创建 Notion Integration

1. 前往 [Notion My Integrations](https://www.notion.so/my-integrations) 创建一个 Integration。
2. 记录生成的 **Internal Integration Secret**（即 `NOTION_API_KEY`）。
3. 打开你想同步的 **根页面**，点击右上角 `···` → `Connect to` → 选择你的 Integration，使其能访问整个页面树。
4. 从根页面的 URL 中提取 **Page ID**（URL 末尾的 32 位十六进制字符串），即 `NOTION_ROOT_PAGE_ID`。

### 3. 准备目标私有仓库

1. 创建（或选择）一个用于存放文档的私有仓库（如 `my-org/my-docs`）。
2. 生成一个对该仓库有 **写权限** 的 [Personal Access Token (classic)](https://github.com/settings/tokens)，勾选 `repo` 权限，即 `TARGET_PAT`。
3. 决定文档要推送到的分支名，即 `TARGET_BRANCH`（如 `main`）。

### 4. 配置 GitHub Secrets

在本代码仓库的 **Settings → Secrets and variables → Actions** 中添加以下 Secrets：

| Secret 名称            | 说明                                              |
|------------------------|---------------------------------------------------|
| `NOTION_API_KEY`       | Notion Integration 的 Internal Integration Secret |
| `NOTION_ROOT_PAGE_ID`  | 要同步的根页面 ID                                 |
| `TARGET_REPO`          | 目标仓库，格式 `owner/repo`（如 `my-org/my-docs`）|
| `TARGET_BRANCH`        | 目标仓库的目标分支（如 `main`）                   |
| `TARGET_PAT`           | 对目标仓库有写权限的 Personal Access Token        |

### 5. 触发同步

- **定时自动同步**：workflow 已配置为每天 00:00 UTC 自动运行。
- **手动触发**：进入本仓库的 **Actions** 页面 → 选择 `Notion to GitHub Sync` → 点击 **Run workflow**。

---

## 导出结构说明

脚本从 `NOTION_ROOT_PAGE_ID` 开始，按照 Notion 页面的父子层级递归导出：

- **有子页面的页面** → 创建同名子目录，页面自身内容写入该目录下的 `index.md`
- **叶子页面（无子页面）** → 直接写为 `页面标题.md`

示例输出结构：

```
target-repo/
└── 我的知识库/          ← 根页面目录
    ├── index.md         ← 根页面内容
    ├── 项目规划/        ← 有子页面的页面
    │   ├── index.md
    │   ├── 第一期.md
    │   └── 第二期.md
    └── 日常笔记.md      ← 叶子页面
```

---

## 支持的 Notion 块类型

| Notion 块类型       | Markdown 输出       |
|--------------------|---------------------|
| paragraph          | 普通段落            |
| heading_1/2/3      | `#` / `##` / `###`  |
| bulleted_list_item | `- 列表项`          |
| numbered_list_item | `1. 列表项`         |
| to_do              | `- [ ]` / `- [x]`  |
| code               | ` ```lang\n...\n``` ` |
| quote              | `> 引用`            |
| callout            | `> emoji 内容`      |
| divider            | `---`               |
| image              | `![caption](url)`   |
| bookmark           | `[caption](url)`    |
| toggle             | 纯文本（展开内容）  |

---

## 验收标准

- ✅ 触发 workflow 后，文档文件**不会**提交到本仓库
- ✅ 文档能被提交到 `TARGET_REPO` 的 `TARGET_BRANCH` 分支
- ✅ Notion 页面的父子层级结构在文件系统中被完整保留
- ✅ 无变更时工作流静默跳过提交，不会报错失败
- ✅ 本仓库 workflow 权限设置为 `contents: read`，最小权限原则
