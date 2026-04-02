"""
notion_sync.py — Sync a Notion page tree to a local directory.

Required environment variables:
    NOTION_API_KEY       — Notion Integration secret token
    NOTION_ROOT_PAGE_ID  — ID of the root Notion page to start from
    OUTPUT_DIR           — Local directory to write Markdown files into
                           (defaults to "notion_pages" in the current directory)
"""

import os
import re
import sys
from pathlib import Path

from notion_client import Client

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_ROOT_PAGE_ID = os.environ["NOTION_ROOT_PAGE_ID"]
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "notion_pages"))

notion = Client(auth=NOTION_API_KEY)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_filename(name: str) -> str:
    """Convert a page title into a filesystem-safe name."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip(". ")
    return name or "Untitled"


def get_page_title(page: dict) -> str:
    """Extract the plain-text title from a Notion page object."""
    try:
        props = page.get("properties", {})
        for key in ("title", "Name"):
            if key in props:
                title_blocks = props[key].get("title", [])
                if title_blocks:
                    return "".join(b.get("plain_text", "") for b in title_blocks)
    except Exception:
        pass
    return "Untitled"


def rich_text_to_md(rich_texts: list) -> str:
    """Convert a Notion rich_text array to a Markdown string."""
    parts = []
    for rt in rich_texts:
        text = rt.get("plain_text", "")
        ann = rt.get("annotations", {})
        if ann.get("code"):
            text = f"`{text}`"
        if ann.get("bold"):
            text = f"**{text}**"
        if ann.get("italic"):
            text = f"*{text}*"
        if ann.get("strikethrough"):
            text = f"~~{text}~~"
        href = rt.get("href")
        if href:
            text = f"[{text}]({href})"
        parts.append(text)
    return "".join(parts)


def block_to_md(block: dict) -> str:
    """Convert a single Notion block to a Markdown line (or empty string)."""
    btype = block.get("type", "")
    data = block.get(btype, {})

    if btype == "paragraph":
        return rich_text_to_md(data.get("rich_text", []))
    if btype == "heading_1":
        return "# " + rich_text_to_md(data.get("rich_text", []))
    if btype == "heading_2":
        return "## " + rich_text_to_md(data.get("rich_text", []))
    if btype == "heading_3":
        return "### " + rich_text_to_md(data.get("rich_text", []))
    if btype == "bulleted_list_item":
        return "- " + rich_text_to_md(data.get("rich_text", []))
    if btype == "numbered_list_item":
        return "1. " + rich_text_to_md(data.get("rich_text", []))
    if btype == "to_do":
        checked = "x" if data.get("checked") else " "
        return f"- [{checked}] " + rich_text_to_md(data.get("rich_text", []))
    if btype == "toggle":
        return rich_text_to_md(data.get("rich_text", []))
    if btype == "code":
        lang = data.get("language", "")
        code = rich_text_to_md(data.get("rich_text", []))
        return f"```{lang}\n{code}\n```"
    if btype == "quote":
        return "> " + rich_text_to_md(data.get("rich_text", []))
    if btype == "callout":
        emoji = (data.get("icon") or {}).get("emoji", "")
        text = rich_text_to_md(data.get("rich_text", []))
        return f"> {emoji} {text}".strip()
    if btype == "divider":
        return "---"
    if btype == "image":
        url = (data.get("file") or {}).get("url") or (data.get("external") or {}).get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        return f"![{caption}]({url})"
    if btype == "bookmark":
        url = data.get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        return f"[{caption or url}]({url})"
    # child_page / child_database are handled by recursion, not inline content
    return ""


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------

def fetch_all_children(block_id: str) -> list:
    """Fetch all child blocks for a given block/page ID (handles pagination)."""
    blocks = []
    cursor = None
    while True:
        kwargs = {"block_id": block_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = notion.blocks.children.list(**kwargs)
        blocks.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return blocks


def sync_page(page_id: str, output_path: Path, depth: int = 0) -> None:
    """
    Recursively sync a Notion page and its descendants into `output_path`.

    * Pages that have child pages become a sub-directory; their own content is
      written to ``index.md`` inside that directory.
    * Leaf pages (no child pages) are written as a single ``<title>.md`` file.
    """
    try:
        page = notion.pages.retrieve(page_id=page_id)
    except Exception as exc:
        print(f"{'  ' * depth}ERROR retrieving {page_id}: {exc}", file=sys.stderr)
        return

    title = get_page_title(page)
    safe_title = safe_filename(title)
    indent = "  " * depth
    print(f"{indent}Syncing: {title}")

    # Fetch all direct children once
    all_blocks = fetch_all_children(page_id)

    # Separate inline content from child-page references
    content_lines: list[str] = []
    child_page_blocks: list[dict] = []

    for block in all_blocks:
        btype = block.get("type", "")
        if btype in ("child_page", "child_database"):
            child_page_blocks.append(block)
        else:
            line = block_to_md(block)
            content_lines.append(line)

    content = "\n".join(content_lines).strip()
    md_body = f"# {title}\n\n{content}\n" if content else f"# {title}\n"

    if child_page_blocks:
        # This page has children → write to a sub-directory
        page_dir = output_path / safe_title
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.md").write_text(md_body, encoding="utf-8")
        for child_block in child_page_blocks:
            sync_page(child_block["id"], page_dir, depth + 1)
    else:
        # Leaf page → single Markdown file
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / f"{safe_title}.md").write_text(md_body, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory : {OUTPUT_DIR.resolve()}")
    print(f"Root page ID     : {NOTION_ROOT_PAGE_ID}")
    sync_page(NOTION_ROOT_PAGE_ID, OUTPUT_DIR)
    print("Sync complete!")


if __name__ == "__main__":
    main()
