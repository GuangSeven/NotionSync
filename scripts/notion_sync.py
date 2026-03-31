# scripts/notion_sync.py

from notion_client import Client
import os

# 获取环境变量中的 Notion API Key 和页面 ID
NOTION_API_KEY = os.environ["NOTION_API_KEY"]
PAGE_ID = os.environ["PAGE_ID"]

# 初始化 Notion 客户端
notion = Client(auth=NOTION_API_KEY)

# 拉取页面内容
def fetch_notion_page(page_id):
    page = notion.blocks.children.list(block_id=PAGE_ID)
    content = []
    for block in page['results']:
        if block["type"] == "paragraph":
            content.append(block["paragraph"]["text"][0]["text"]["content"])
    return "\n".join(content)

# 将内容写入 Markdown 文件
def write_to_markdown(content, filename="NOTION_SYNC.md"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Synced from Notion\n\n")
        f.write(content)

if __name__ == "__main__":
    notion_content = fetch_notion_page(PAGE_ID)
    write_to_markdown(notion_content)
