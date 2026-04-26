# app/api/wiki.py
"""Wiki read-only routes — migrated from server.py."""
from pathlib import Path
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse
from app.services import build_index, build_graph, build_path_cache
from app.config import WIKI_DIR, PUBLIC_DIR, RAW_DIR, WIKI_CATEGORIES

# Category display name mapping (not in config.py)
CATEGORY_NAMES = {
    "3dgs": "3DGS",
    "avm": "AVM",
    "calibration": "标定",
    "perception": "感知",
    "tracking": "跟踪",
    "fusion": "融合",
    "platform": "平台",
    "tools": "工具",
}

router = APIRouter(tags=["wiki"])


@router.get("/api/index")
async def api_index():
    """JSON API: return list of all wiki pages."""
    return build_index()


@router.get("/api/graph")
async def api_graph():
    """JSON API: return graph data."""
    return build_graph()


@router.get("/api/wiki-path-map")
async def api_path_map():
    """JSON API: return filename stem/title to wiki path mapping."""
    return build_path_cache()


@router.get("/wiki/{path:path}")
async def serve_wiki(path: str):
    """Serve a wiki page as raw markdown."""
    file_path = WIKI_DIR / f"{path}.md" if not path.endswith(".md") else WIKI_DIR / path
    if not file_path.exists():
        return Response(status_code=404, content=f"Wiki page not found: {path}")
    content = file_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/markdown; charset=utf-8")


@router.get("/raw-file/{path:path}")
async def serve_raw_file(path: str):
    """Serve a raw file as markdown."""
    file_path = RAW_DIR / path
    if not file_path.exists():
        return Response(status_code=404, content=f"Raw file not found: {path}")
    content = file_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/markdown; charset=utf-8")


@router.get("/raw")
@router.get("/raw.html")
async def serve_raw_browser():
    """Serve the raw file browser HTML page."""
    from app.api.upload import generate_raw_browser_html
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=generate_raw_browser_html())


@router.get("/")
async def index():
    """Serve Docsify home page."""
    index_path = PUBLIC_DIR / "index.html"
    if not index_path.exists():
        return Response(status_code=404, content="Docsify index.html not found")
    return FileResponse(str(index_path), media_type="text/html; charset=utf-8")


@router.get("/_sidebar.md")
async def sidebar():
    """Generate dynamic sidebar."""
    pages = build_index()
    categories = {}
    for info in pages:
        cat = info["category"]
        categories.setdefault(cat, []).append(info)

    lines = ["", "* **<a href='/api/upload' target='_blank'>📝 上传文件</a>**", ""]
    for cat_key in sorted(categories.keys()):
        cat_name = CATEGORY_NAMES.get(cat_key, cat_key.upper())
        lines.append(f"* **{cat_name}**")
        for item in sorted(categories[cat_key], key=lambda x: x["title"]):
            lines.append(f"  * [{item['title']}](wiki/{item['path']})")
        lines.append("")
    content = "\n".join(lines)
    return Response(content=content, media_type="text/markdown; charset=utf-8")


@router.get("/README.md")
async def readme():
    """Serve README as Docsify home content."""
    pages = build_index()
    cats = set(p["category"] for p in pages)
    text = f"""# AI 知识库

> 自动驾驶标定与感知知识管理系统

## 快捷操作

[📝 上传文件 / 新建文档](/api/upload) — 上传 raw md 文件，自动调用 LLM 分析生成 wiki 页面

## 导航

请从左侧导航栏选择分类浏览，或使用顶部搜索框。

---

| 统计 | 数量 |
|------|------|
| 知识文档 | {len(pages)} 篇 |
| 分类 | {len(cats)} 个 |
"""
    return Response(content=text, media_type="text/markdown; charset=utf-8")


@router.get("/docsify-theme.css")
async def theme_css():
    """Serve theme CSS."""
    css_path = PUBLIC_DIR / "docsify-theme.css"
    if not css_path.exists():
        return Response(status_code=404, content="Theme CSS not found")
    return FileResponse(str(css_path), media_type="text/css; charset=utf-8")


@router.get("/graph")
@router.get("/graph.html")
async def graph_page():
    """Serve relationship graph HTML."""
    graph_path = PUBLIC_DIR / "graph.html"
    if not graph_path.exists():
        return Response(status_code=404, content="graph.html not found")
    return FileResponse(str(graph_path), media_type="text/html; charset=utf-8")


@router.get("/login")
@router.get("/login.html")
async def login_page():
    """Serve login page."""
    login_path = PUBLIC_DIR / "login.html"
    if not login_path.exists():
        return Response(status_code=404, content="login.html not found")
    return FileResponse(str(login_path), media_type="text/html; charset=utf-8")


@router.get("/favicon.ico")
async def favicon():
    return Response(status_code=404)
