# app/services.py
"""Shared wiki building logic — migrated from server.py."""
import re
from pathlib import Path
from app.config import WIKI_DIR


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown text."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            val = val.strip().strip("[]").strip("'\"")
            fm[key.strip()] = val
    return fm, m.group(2)


def build_path_cache() -> dict[str, str]:
    """Build mapping from filename stem/title to wiki path."""
    cache = {}
    if not WIKI_DIR.exists():
        return cache
    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        rel = str(md_file.relative_to(WIKI_DIR))
        cache[md_file.stem] = rel
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            if "title" in fm:
                cache[fm["title"]] = rel
        except Exception:
            pass
    return cache


def build_index() -> list[dict]:
    """Scan wiki directory and build page list."""
    pages = []
    if not WIKI_DIR.exists():
        return pages

    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        rel = md_file.relative_to(WIKI_DIR)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            pages.append({
                "title": fm.get("title", md_file.stem),
                "category": category,
                "tags": fm.get("tags", ""),
                "updated": fm.get("updated", ""),
                "path": str(rel),
            })
        except Exception:
            pages.append({
                "title": md_file.stem,
                "category": category,
                "tags": "",
                "updated": "",
                "path": str(rel),
            })
    return pages


def build_graph() -> dict:
    """Build graph data (nodes + edges) for relationship graph."""
    pages = build_index()
    path_cache = build_path_cache()

    nodes = []
    edges = []
    edge_set = set()

    wiki_content = {}
    for info in pages:
        file_path = WIKI_DIR / info["path"]
        try:
            wiki_content[info["path"]] = file_path.read_text(encoding="utf-8")
        except Exception:
            wiki_content[info["path"]] = ""

    for info in pages:
        nodes.append({
            "id": info["title"],
            "key": info["path"],
            "category": info["category"],
            "tags": info["tags"],
            "updated": info["updated"],
        })

    for path, content in wiki_content.items():
        related_section = re.search(r"##\s+相关页面\s*\n([\s\S]*)", content)
        if not related_section:
            continue
        related_text = related_section.group(1)

        wikilinks = re.findall(r"\[\[([^\]|]+)", related_text)
        mdlinks = re.findall(r"\]\((\.\/|\.\.\/[^\)]+\/)([^\)]+)\.md\)", related_text)

        all_targets = set()
        for key in wikilinks:
            key = key.strip()
            if key in path_cache:
                all_targets.add(path_cache[key])
        for prefix, target in mdlinks:
            target_stem = target.rsplit("/", 1)[-1] if "/" in target else target
            if target_stem in path_cache:
                all_targets.add(path_cache[target_stem])

        for target_path in all_targets:
            edge_key = (path, target_path)
            if path != target_path and edge_key not in edge_set:
                edge_set.add(edge_key)
                edges.append({"source": path, "target": target_path})

    return {"nodes": nodes, "edges": edges}
