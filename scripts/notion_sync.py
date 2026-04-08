import os
import re
import sys
from pathlib import Path
from notion_client import Client
from notion_client.errors import APIResponseError

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
# 支持多顶级页面：NOTION_ROOT_PAGE_IDS（逗号分隔），兼容旧版单页面 NOTION_ROOT_PAGE_ID
_RAW_IDS = os.environ.get("NOTION_ROOT_PAGE_IDS") or os.environ.get("NOTION_ROOT_PAGE_ID", "")
OUT_DIR = Path(os.environ.get("OUT_DIR", "notion_export"))

notion = Client(auth=NOTION_API_KEY)

INVALID_CHARS = r'[\\/:*?"<>|#%&{}$!@+=`~]'

MAX_FILENAME_LENGTH = 120
DEFAULT_IMAGE_ALT = "图片"

# 两个正则分别匹配无横线（32位）和带横线（UUID）两种格式
_HEX32_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def normalize_page_id(page_id: str) -> str:
    """
    将 page id 标准化为 Notion API 接受的格式。
    接受两种输入：
      - 32 位无横线：e4536863fdb049e38526a681651d8776
      - UUID 格式  ：e4536863-fdb0-49e3-8526-a681651d8776
    返回 UUID 格式字符串，或在格式不正确时打印诊断信息并退出。
    """
    pid = page_id.strip()
    raw = pid.replace("-", "").lower()
    if _UUID_RE.match(pid) or _HEX32_RE.match(pid):
        # 统一转换为 UUID 格式
        return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"
    print(
        "\n❌ 错误：页面 ID 格式不正确！\n"
        f"   当前值：{pid!r}\n"
        "   正确格式（从 Notion 页面 URL 最后一段提取）：\n"
        "     无横线（32位）：e4536863fdb049e38526a681651d8776\n"
        "     UUID 格式     ：e4536863-fdb0-49e3-8526-a681651d8776\n"
        "   示例 URL：\n"
        "     https://www.notion.so/your-workspace/PageTitle-e4536863fdb049e38526a681651d8776\n"
        "   操作步骤：\n"
        "     1. 在浏览器打开你的 Notion 页面\n"
        "     2. 复制 URL 末尾的 32 位十六进制字符串（紧跟在最后一个 '-' 之后或直接是结尾）\n"
        "     3. 将该值填入 GitHub Secrets 中的 NOTION_ROOT_PAGE_IDS\n",
        file=sys.stderr,
    )
    sys.exit(1)


def validate_notion_token():
    """
    验证 NOTION_API_KEY 是否有效，失败时打印修复步骤并退出。
    单独验证 token，不阻塞后续各页面的可访问性检查。
    """
    try:
        me = notion.users.me()
        print(f"✅ Notion token 有效，当前 integration：{me.get('name', '(未知)')}")
    except APIResponseError as e:
        print(
            "\n❌ Notion API Token 无效或权限不足！\n"
            f"   错误详情：{e}\n"
            "   修复步骤：\n"
            "     1. 前往 https://www.notion.so/my-integrations 确认 integration 存在\n"
            "     2. 复制正确的 'Internal Integration Secret' 并更新 GitHub Secrets 中的 NOTION_API_KEY\n"
            "     3. 确保该 integration 所在 workspace 与目标页面一致\n",
            file=sys.stderr,
        )
        sys.exit(1)


def safe_name(name: str) -> str:
    """将页面标题转换为合法的文件/目录名"""
    name = (name or "Untitled").strip()
    name = re.sub(INVALID_CHARS, "_", name)
    name = re.sub(r"\s+", " ", name)
    return name[:MAX_FILENAME_LENGTH] or "Untitled"


def get_page_title(page_obj: dict) -> str:
    """从页面对象中提取标题"""
    props = page_obj.get("properties", {})
    for _, v in props.items():
        if v.get("type") == "title":
            arr = v.get("title", [])
            if arr:
                return "".join([x.get("plain_text", "") for x in arr]).strip() or "Untitled"
    return "Untitled"


def list_block_children(block_id: str):
    """分页获取 block 的所有子块"""
    results = []
    cursor = None
    while True:
        resp = notion.blocks.children.list(block_id=block_id, start_cursor=cursor, page_size=100)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return results

def rich_text_to_plain(rt) -> str:
    """将 rich_text 数组转换为纯文本"""
    return "".join([x.get("plain_text", "") for x in rt or []])


def block_text_summary(block: dict) -> str:
    """提取 block 的纯文本摘要，用于组合型结构（如 column_list）"""
    t = block["type"]
    b = block.get(t, {})
    if t in {
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "quote",
        "code",
    }:
        return rich_text_to_plain(b.get("rich_text"))
    if t == "to_do":
        checked = b.get("checked", False)
        mark = "x" if checked else " "
        return f"[{mark}] " + rich_text_to_plain(b.get("rich_text"))
    if t == "image":
        return render_image_md(b)
    return ""


def escape_md_table_cell(text: str) -> str:
    """转义 Markdown 表格单元格中的特殊字符"""
    return text.replace("|", "\\|").replace("\n", "<br>").strip()


def get_notion_file_url(file_property: dict) -> str:
    """提取 Notion 文件属性（external/file）的可访问 URL"""
    if not isinstance(file_property, dict):
        return ""
    if file_property.get("type") == "external":
        return file_property.get("external", {}).get("url", "")
    if file_property.get("type") == "file":
        return file_property.get("file", {}).get("url", "")
    return ""


def render_image_md(image_property: dict) -> str:
    """将 Notion image 属性渲染为 Markdown 图片语法"""
    url = get_notion_file_url(image_property)
    if not url:
        return ""
    caption = rich_text_to_plain(image_property.get("caption")).strip() or DEFAULT_IMAGE_ALT
    return f"![{caption}]({url})"


def block_to_md(block: dict) -> str:
    """将单个 Notion block 转换为 Markdown 文本"""
    t = block["type"]
    b = block.get(t, {})
    if t == "paragraph":
        return rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "heading_1":
        return "# " + rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "heading_2":
        return "## " + rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "heading_3":
        return "### " + rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "bulleted_list_item":
        return "- " + rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "numbered_list_item":
        return "1. " + rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "to_do":
        checked = b.get("checked", False)
        mark = "x" if checked else " "
        return f"- [{mark}] " + rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "quote":
        return "> " + rich_text_to_plain(b.get("rich_text")) + "\n"
    if t == "code":
        lang = b.get("language", "")
        return f"```{lang}\n{rich_text_to_plain(b.get('rich_text'))}\n```\n"
    if t == "image":
        image_md = render_image_md(b)
        return f"{image_md}\n" if image_md else ""
    if t == "column_list":
        columns = list_block_children(block["id"])
        cells = []
        for col in columns:
            if col.get("type") != "column":
                continue
            col_children = list_block_children(col["id"])
            parts = []
            for child in col_children:
                text = block_text_summary(child).strip()
                if text:
                    parts.append(escape_md_table_cell(text))
            if parts:
                cells.append("<br>".join(parts))
        if not cells:
            return ""
        headers = [""] * len(cells)
        return (
            "| " + " | ".join(headers) + " |\n"
            "| " + " | ".join(["----"] * len(headers)) + " |\n"
            "| " + " | ".join(cells) + " |\n"
        )
    if t == "divider":
        return "---\n"
    return f"<!-- unsupported block: {t} -->\n"


def export_page_recursive(page_id: str, parent_dir: Path):
    """
    递归导出 Notion 页面及其所有子页面，保持层级目录结构。
    每个页面在目标目录下创建以页面标题命名的子目录，
    页面内容写入该目录的 index.md 文件。
    """
    try:
        page = notion.pages.retrieve(page_id=page_id)
    except APIResponseError as e:
        status = getattr(e, "status", None) or getattr(e, "code", None)
        print(
            f"  ⚠️  跳过页面 {page_id}（无法访问，{status}）：{e}",
            file=sys.stderr,
        )
        return
    title = safe_name(get_page_title(page))
    page_dir = parent_dir / title
    page_dir.mkdir(parents=True, exist_ok=True)

    md_lines = [f"# {title}\n\n"]
    children = list_block_children(page_id)

    child_pages = []
    for blk in children:
        if blk.get("type") == "child_page":
            child_pages.append(blk)
        else:
            md_lines.append(block_to_md(blk))

    (page_dir / "index.md").write_text("".join(md_lines), encoding="utf-8")
    print(f"  导出：{page_dir / 'index.md'}")

    for blk in child_pages:
        export_page_recursive(blk["id"], page_dir)


def main():
    if not _RAW_IDS.strip():
        print(
            "❌ 未配置页面 ID！请设置环境变量 NOTION_ROOT_PAGE_IDS（逗号分隔多个页面 ID）"
            " 或 NOTION_ROOT_PAGE_ID（单页面，兼容旧版）。",
            file=sys.stderr,
        )
        sys.exit(1)

    page_ids = [normalize_page_id(pid.strip()) for pid in _RAW_IDS.split(",") if pid.strip()]
    if not page_ids:
        print("❌ 未解析到有效的页面 ID，请检查 NOTION_ROOT_PAGE_IDS 的值。", file=sys.stderr)
        sys.exit(1)

    validate_notion_token()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for page_id in page_ids:
        print(f"开始从根页面 {page_id} 递归导出...")
        export_page_recursive(page_id, OUT_DIR)

    print(f"全部导出完成，文件保存到：{OUT_DIR}")


if __name__ == "__main__":
    main()
