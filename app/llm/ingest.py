# app/llm/ingest.py
"""LLM ingest pipeline: analyze raw md -> generate wiki page."""
import json
import re
from pathlib import Path
from datetime import datetime
from app.config import (
    WIKI_DIR, RAW_DIR, INDEX_FILE, LOG_FILE, WIKI_CATEGORIES, KB_ROOT
)
from app.llm.client import call_llm, extract_json_from_response
from app.services import build_index, parse_frontmatter
from app.tasks import update_task


INGEST_PROMPT = """你是一个知识库 ingest 引擎。请分析以下 raw markdown 文件，并生成符合规范的 wiki 页面。

要求：
1. 提取关键概念、公式、算法、架构图
2. 判断所属分类（从以下选择一个：{categories}）
3. 搜索现有 wiki 内容，决定创建新页面还是更新已有页面
4. 生成 wiki 页面内容，包含：
   - YAML frontmatter（title, category, tags, created, updated, sources）
   - 结构化的正文内容（中文）
   - ## 相关页面 章节，链接到相关 wiki 页面（使用 [[wikilink]] 格式）

当前 wiki 索引如下：
{index_content}

Raw 文件内容：
{raw_content}

请只以 JSON 格式返回，不要有其他内容：
```json
{{
  "category": "分类",
  "filename": "kebab-case-英文文件名.md",
  "action": "create",
  "target_path": "分类/文件名",
  "wiki_content": "完整的 wiki 页面内容（markdown 字符串，换行用 \\n）",
  "title": "中文标题"
}}
```"""


async def run_ingest(task_id: str, raw_rel_path: str):
    """Execute the full ingest pipeline for a raw file.

    Args:
        task_id: Task ID for status tracking
        raw_rel_path: Relative path under raw/ (e.g., "avm_calib/某文件.md")
    """
    update_task(task_id, "processing")

    try:
        # 1. Read raw file
        raw_path = RAW_DIR / raw_rel_path
        if not raw_path.exists():
            update_task(task_id, "failed", error=f"文件不存在: {raw_rel_path}")
            return

        raw_content = raw_path.read_text(encoding="utf-8")

        # 2. Read current index
        pages = build_index()
        index_lines = []
        for p in pages:
            index_lines.append(f"- {p['title']} ({p['path']})")
        index_content = "\n".join(index_lines) if index_lines else "（暂无 wiki 页面）"

        # 3. Call LLM
        categories_str = ", ".join(WIKI_CATEGORIES)
        prompt = INGEST_PROMPT.format(
            categories=categories_str,
            index_content=index_content,
            raw_content=raw_content[:15000],  # limit to avoid token overflow
        )

        response = await call_llm([
            {"role": "user", "content": prompt}
        ], timeout=180.0)

        # 4. Parse LLM response
        result = extract_json_from_response(response)

        category = result.get("category", "tools")
        filename = result.get("filename", raw_path.stem + ".md")
        wiki_content = result.get("wiki_content", "")
        title = result.get("title", filename.replace(".md", ""))

        if not wiki_content:
            update_task(task_id, "failed", error="LLM 未生成有效的 wiki 内容")
            return

        # 5. Validate wiki content has frontmatter
        if not wiki_content.startswith("---"):
            # Try to prepend minimal frontmatter
            frontmatter = f"""---
title: {title}
category: {category}
tags: []
created: {datetime.now().strftime('%Y-%m-%d')}
updated: {datetime.now().strftime('%Y-%m-%d')}
sources: [raw/{raw_rel_path}]
---

"""
            wiki_content = frontmatter + wiki_content

        # 6. Write wiki file
        wiki_category_dir = WIKI_DIR / category
        wiki_category_dir.mkdir(parents=True, exist_ok=True)
        wiki_file_path = wiki_category_dir / filename

        # Handle conflict
        if wiki_file_path.exists():
            stem = wiki_file_path.stem
            wiki_file_path = wiki_category_dir / f"{stem}.conflict.md"

        wiki_file_path.write_text(wiki_content, encoding="utf-8")

        # 7. Update index.md
        _update_index(category, filename, title)

        # 8. Append log.md
        _append_log(category, filename, title, raw_rel_path)

        # 9. Mark completed
        update_task(task_id, "completed", result={
            "wiki_path": f"{category}/{filename}",
            "title": title,
            "action": "create",
        })

    except Exception as e:
        update_task(task_id, "failed", error=str(e))


def _update_index(category: str, filename: str, title: str):
    """Add entry to index.md."""
    index_path = INDEX_FILE
    if not index_path.exists():
        index_path.write_text(f"# AI 知识库索引\n", encoding="utf-8")

    content = index_path.read_text(encoding="utf-8")
    category_names = {
        "3dgs": "3D Gaussian Splatting",
        "avm": "AVM 环视系统",
        "calibration": "相机标定",
        "perception": "感知与检测",
        "tracking": "跟踪与滤波",
        "fusion": "传感器融合",
        "platform": "嵌入式平台",
        "tools": "工具与优化",
    }
    cat_name = category_names.get(category, category.upper())

    # Check if category section exists
    section_header = f"## {cat_name}"
    if section_header in content:
        # Insert after the header's table header line
        pattern = rf"(## {re.escape(cat_name)}\n\n\| 页面 \| 摘要 \| 更新日期 \|\n)"
        new_entry = f"| [{title}](wiki/{category}/{filename}) | 新摄入 | {datetime.now().strftime('%Y-%m-%d')} |\n"
        content = re.sub(pattern, rf"\1{new_entry}", content)
    else:
        # Add new category section
        new_section = f"\n## {cat_name}\n\n| 页面 | 摘要 | 更新日期 |\n|------|------|----------|\n| [{title}](wiki/{category}/{filename}) | 新摄入 | {datetime.now().strftime('%Y-%m-%d')} |\n"
        content += new_section

    index_path.write_text(content, encoding="utf-8")


def _append_log(category: str, filename: str, title: str, raw_rel_path: str):
    """Append ingest record to log.md."""
    log_path = LOG_FILE
    if not log_path.exists():
        log_path.write_text("# 操作日志\n", encoding="utf-8")

    record = f"\n## [{datetime.now().strftime('%Y-%m-%d')}] ingest | {title}\n"
    record += f"- 来源: raw/{raw_rel_path}\n"
    record += f"- 分类: {category}\n"
    record += f"- 目标: wiki/{category}/{filename}\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(record)
