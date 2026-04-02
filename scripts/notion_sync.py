import os
import re
from pathlib import Path
from notion_client import Client

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_ROOT_PAGE_ID = os.environ["NOTION_ROOT_PAGE_ID"]
OUT_DIR = Path(os.environ.get("OUT_DIR", "notion_export"))

notion = Client(auth=NOTION_API_KEY)

INVALID_CHARS = r'[\\/:*?"<>|#%&{}$!@+=`~]'

MAX_FILENAME_LENGTH = 120


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

    # Separate inline content from child-page references
    content_lines: list[str] = []
    child_page_blocks: list[dict] = []

def rich_text_to_plain(rt) -> str:
    """将 rich_text 数组转换为纯文本"""
    return "".join([x.get("plain_text", "") for x in rt or []])


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
    if t == "divider":
        return "---\n"
    return f"<!-- unsupported block: {t} -->\n"


def export_page_recursive(page_id: str, parent_dir: Path):
    """
    递归导出 Notion 页面及其所有子页面，保持层级目录结构。
    每个页面在目标目录下创建以页面标题命名的子目录，
    页面内容写入该目录的 index.md 文件。
    """
    page = notion.pages.retrieve(page_id=page_id)
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

    # 递归处理子页面
    for cp in child_pages:
        export_page_recursive(cp["id"], page_dir)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"开始从根页面 {NOTION_ROOT_PAGE_ID} 递归导出...")
    export_page_recursive(NOTION_ROOT_PAGE_ID, OUT_DIR)
    print(f"导出完成，文件保存到：{OUT_DIR}")


if __name__ == "__main__":
    main()
