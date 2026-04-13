#!/usr/bin/env python3
"""
Lightweight HTTP server for the AI Knowledge Base.
Serves raw markdown files for Docsify client-side rendering.
No dependencies beyond Python stdlib.

Usage:
    python server.py              # serves on port 8080
    python server.py --port 9000  # serves on port 9000
    python server.py --host 0.0.0.0  # accessible on LAN
"""

import os
import sys
import re
import json
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

KB_ROOT = Path(__file__).parent
WIKI_DIR = KB_ROOT / "wiki"
PUBLIC_DIR = KB_ROOT / "public"

CATEGORY_NAMES = {
    "3dgs": "3D Gaussian Splatting",
    "avm": "AVM 环视系统",
    "calibration": "相机标定",
    "perception": "感知与检测",
    "tracking": "跟踪与滤波",
    "fusion": "传感器融合",
    "platform": "嵌入式平台",
    "tools": "工具与优化",
}


def parse_frontmatter(text):
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


# Cached mapping: {filename_stem: "category/filename", title: "category/filename"}
_path_cache = None


def _build_path_cache():
    """Build a mapping from filename stem and title to full relative path."""
    global _path_cache
    if _path_cache is not None:
        return _path_cache
    _path_cache = {}
    if not WIKI_DIR.exists():
        return _path_cache
    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        rel = str(md_file.relative_to(WIKI_DIR))
        _path_cache[md_file.stem] = rel
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            if "title" in fm:
                _path_cache[fm["title"]] = rel
        except Exception:
            pass
    return _path_cache


def build_index():
    """Scan wiki directory and build category-indexed page list."""
    pages = {}
    if not WIKI_DIR.exists():
        return pages

    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        rel = md_file.relative_to(WIKI_DIR)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            title = fm.get("title", md_file.stem)
            tags = fm.get("tags", "")
            pages[str(rel)] = {
                "title": title,
                "category": category,
                "tags": tags,
                "updated": fm.get("updated", ""),
                "path": str(rel),
            }
        except Exception:
            pages[str(rel)] = {
                "title": md_file.stem,
                "category": category,
                "tags": "",
                "updated": "",
                "path": str(rel),
            }
    return pages


def generate_sidebar():
    """Generate _sidebar.md content organized by category."""
    pages = build_index()
    categories = {}
    for path, info in pages.items():
        cat = info["category"]
        categories.setdefault(cat, []).append(info)

    lines = [""]  # leading newline for docsify
    for cat_key in sorted(categories.keys()):
        cat_name = CATEGORY_NAMES.get(cat_key, cat_key.upper())
        lines.append(f"* **{cat_name}**")
        for item in sorted(categories[cat_key], key=lambda x: x["title"]):
            lines.append(f"  * [{item['title']}](wiki/{item['path']})")
        lines.append("")
    return "\n".join(lines)


class KBHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(KB_ROOT), **kwargs)

    def do_GET(self):
        # Decode URL (handle double-encoding from Docsify hash router)
        path = unquote(unquote(self.path))
        # Strip query parameters and leading double-slash
        path = path.split("?")[0]
        if path.startswith("//"):
            path = path[1:]

        if path == "/" or path == "/index.html":
            self.serve_docsify_home()
        elif path == "/_sidebar.md":
            self.serve_sidebar()
        elif path == "/README.md":
            self.serve_readme()
        elif path.startswith("/docsify-theme.css"):
            self.serve_theme_css()
        elif path.startswith("/wiki/"):
            self.serve_wiki_raw(path[len("/wiki/"):])
        elif path == "/api/index":
            self.serve_api_index()
        elif path == "/api/wiki-path-map":
            self.serve_path_map()
        elif path == "/api/graph":
            self.serve_graph()
        elif path == "/graph" or path == "/graph.html":
            self.serve_graph_page()
        elif path == "/raw" or path == "/raw.html":
            self.serve_raw_browser()
        elif path.startswith("/raw-file/"):
            self.serve_raw_file(path[len("/raw-file/"):])
        else:
            super().do_GET()

    def serve_docsify_home(self):
        """Serve the Docsify SPA from public/index.html."""
        index_path = PUBLIC_DIR / "index.html"
        if not index_path.exists():
            self.send_error(404, "Docsify index.html not found in public/")
            return
        self._serve_file(index_path, "text/html; charset=utf-8")

    def serve_theme_css(self):
        """Serve the Docsify theme CSS from public/docsify-theme.css."""
        css_path = PUBLIC_DIR / "docsify-theme.css"
        if not css_path.exists():
            self.send_error(404, "Theme CSS not found")
            return
        self._serve_file(css_path, "text/css; charset=utf-8")

    def serve_readme(self):
        """Serve README.md as the Docsify home page content."""
        readme = """# AI 知识库

> 自动驾驶标定与感知知识管理系统

## 导航

请从左侧导航栏选择分类浏览，或使用顶部搜索框。

---

| 统计 | 数量 |
|------|------|
"""
        pages = build_index()
        cats = set()
        for p in pages.values():
            cats.add(p["category"])
        readme += f"| 知识文档 | {len(pages)} 篇 |\n"
        readme += f"| 分类 | {len(cats)} 个 |\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(readme.encode("utf-8"))))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(readme.encode("utf-8"))

    def serve_wiki_raw(self, rel_path):
        """Serve a wiki page as raw markdown for Docsify to render."""
        # Handle URLs like "avm/avm-calibration-algorithms?id=_1-2.md" or "avm/avm-calibration-algorithms.md"
        # Docsify sometimes appends .md after query params
        base = rel_path.split("?")[0]
        if base.endswith(".md"):
            file_path = WIKI_DIR / base
        else:
            file_path = WIKI_DIR / (base + ".md")
        if not file_path.exists():
            self.send_error(404, f"Wiki page not found: {rel_path}")
            return
        self._serve_file(file_path, "text/markdown; charset=utf-8")

    def serve_sidebar(self):
        """Serve dynamically generated sidebar markdown."""
        content = generate_sidebar()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def serve_api_index(self):
        """JSON API: return list of all wiki pages."""
        pages = list(build_index().values())
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(pages, ensure_ascii=False).encode())

    def serve_path_map(self):
        """JSON API: return filename_stem/title to wiki path mapping."""
        cache = _build_path_cache()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(cache, ensure_ascii=False).encode())

    def serve_graph_page(self):
        """Serve the relationship graph HTML page."""
        graph_path = PUBLIC_DIR / "graph.html"
        if not graph_path.exists():
            self.send_error(404, "graph.html not found")
            return
        self._serve_file(graph_path, "text/html; charset=utf-8")

    def serve_raw_browser(self):
        """Serve the raw file browser HTML page."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = self._generate_raw_browser_html()
        self.wfile.write(html.encode("utf-8"))

    def serve_raw_file(self, rel_path):
        """Serve a raw file as markdown for Docsify-like rendering."""
        file_path = KB_ROOT / "raw" / rel_path
        if not file_path.exists():
            self.send_error(404, f"Raw file not found: {rel_path}")
            return
        self._serve_file(file_path, "text/markdown; charset=utf-8")

    def serve_graph(self):
        """JSON API: return graph data (nodes + edges) for relationship graph."""
        pages = build_index()
        path_cache = _build_path_cache()

        nodes = []
        edges = []
        edge_set = set()  # dedup

        # Collect all wiki content for link extraction
        wiki_content = {}
        for path, info in pages.items():
            file_path = WIKI_DIR / path
            try:
                wiki_content[path] = file_path.read_text(encoding="utf-8")
            except Exception:
                wiki_content[path] = ""

        # Build nodes
        for path, info in pages.items():
            nodes.append({
                "id": info["title"],
                "key": path,  # relative path like "calibration/epipolar-geometry"
                "category": info["category"],
                "tags": info["tags"],
                "updated": info["updated"],
            })

        # Build edges from [[wikilink]] and markdown links in "相关页面" sections
        for path, content in wiki_content.items():
            # Find the "相关页面" section and content after it
            related_section = re.search(r"##\s+相关页面\s*\n([\s\S]*)", content)
            if not related_section:
                continue
            related_text = related_section.group(1)

            source_path = path
            source_stem = str(WIKI_DIR / path).rsplit("/", 1)[-1].replace(".md", "")

            # Extract [[wikilink|display]] and [[wikilink]] patterns
            wikilinks = re.findall(r"\[\[([^\]|]+)", related_text)
            # Extract markdown links [text](./relative.md) or [text](../cat/relative.md)
            mdlinks = re.findall(r"\]\((\.\/|\.\.\/[^\)]+\/)([^\)]+)\.md\)", related_text)

            all_targets = set()
            for key in wikilinks:
                key = key.strip()
                # Try to resolve via path cache
                if key in path_cache:
                    all_targets.add(path_cache[key])
            for prefix, target in mdlinks:
                # Strip directory prefix to get just filename
                target_stem = target.rsplit("/", 1)[-1] if "/" in target else target
                if target_stem in path_cache:
                    all_targets.add(path_cache[target_stem])

            for target_path in all_targets:
                edge_key = (source_path, target_path)
                if source_path != target_path and edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({"source": source_path, "target": target_path})

        data = {"nodes": nodes, "edges": edges}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _serve_file(self, file_path, content_type):
        """Serve a file with the given content type."""
        text = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(text)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(text)

    def _generate_raw_browser_html(self):
        """Generate an Obsidian-style raw file browser page."""
        raw_dir = KB_ROOT / "raw"
        if not raw_dir.exists():
            return "<p>raw/ directory not found</p>"

        # Scan categories and files
        categories = {}
        for item in sorted(raw_dir.iterdir()):
            if item.is_dir():
                files = sorted([f.name for f in item.iterdir() if f.suffix == ".md"])
                if files:
                    categories[item.name] = files
            elif item.suffix == ".md":
                categories.setdefault("_root", []).append(item.name)

        # Build HTML
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>原始文件浏览</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,400&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --bg: #ffffff; --bg-sidebar: #fafafa; --bg-hover: #eee; --bg-active: #e8e8e8;
    --text: #2c2c2c; --text-secondary: #6b6b6b; --text-muted: #999;
    --border: #e8e8e8; --accent: #7c5cfc;
  }
  body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); overflow: hidden; height: 100vh; display: flex; }
  .sidebar { width: 260px; min-width: 260px; height: 100vh; background: var(--bg-sidebar); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
  .sidebar-header { padding: 12px 16px; border-bottom: 1px solid var(--border); min-height: 48px; display: flex; align-items: center; gap: 8px; }
  .sidebar-header span { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
  .sidebar-tree { flex: 1; overflow-y: auto; padding: 8px 0; }
  .sidebar-tree::-webkit-scrollbar { width: 4px; }
  .sidebar-tree::-webkit-scrollbar-thumb { background: #ddd; border-radius: 2px; }
  .cat-header { display: flex; align-items: center; padding: 4px 12px; cursor: pointer; font-size: 12px; font-weight: 500; color: var(--text-secondary); gap: 4px; user-select: none; }
  .cat-header:hover { background: var(--bg-hover); }
  .cat-chevron { width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; transition: transform 0.15s; flex-shrink: 0; }
  .cat-chevron.open { transform: rotate(90deg); }
  .cat-chevron svg { width: 10px; height: 10px; fill: var(--text-muted); }
  .cat-files { overflow: hidden; max-height: 0; transition: max-height 0.2s; }
  .cat-files.open { max-height: 2000px; }
  .file-item { padding: 3px 12px 3px 32px; font-size: 11.5px; color: var(--text-secondary); cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .file-item:hover { background: var(--bg-hover); color: var(--text); }
  .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .toolbar { height: 48px; display: flex; align-items: center; padding: 0 12px; border-bottom: 1px solid var(--border); }
  .toolbar-btn { width: 30px; height: 30px; border: none; background: transparent; color: var(--text-secondary); cursor: pointer; border-radius: 6px; display: flex; align-items: center; justify-content: center; }
  .toolbar-btn:hover { background: var(--bg-hover); }
  .toolbar-btn svg { width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  .toolbar-title { flex: 1; text-align: center; font-size: 13px; font-weight: 500; color: var(--text-secondary); }
  .content { flex: 1; overflow-y: auto; padding: 24px 32px; }
  .content::-webkit-scrollbar { width: 6px; }
  .content::-webkit-scrollbar-thumb { background: #ddd; border-radius: 3px; }
  .file-content { max-width: 800px; margin: 0 auto; }
  .file-content h1 { font-size: 22px; font-weight: 600; margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
  .file-content h2 { font-size: 18px; font-weight: 600; margin: 20px 0 10px; }
  .file-content h3 { font-size: 15px; font-weight: 600; margin: 16px 0 8px; }
  .file-content h4 { font-size: 14px; font-weight: 600; margin: 12px 0 6px; }
  .file-content p { margin: 8px 0; line-height: 1.7; }
  .file-content ul, .file-content ol { margin: 8px 0; padding-left: 24px; }
  .file-content li { margin: 4px 0; line-height: 1.6; }
  .file-content hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
  .file-content code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: 'Menlo', 'Monaco', 'Courier New', monospace; }
  .file-content pre { background: #f6f6f6; padding: 14px 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; }
  .file-content pre code { background: none; padding: 0; font-size: 13px; line-height: 1.6; }
  .file-content blockquote { border-left: 3px solid #ddd; padding-left: 14px; margin: 12px 0; color: var(--text-secondary); }
  .file-content table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }
  .file-content th, .file-content td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
  .file-content th { background: #f8f8f8; font-weight: 600; }
  .file-content a { color: var(--accent); text-decoration: none; }
  .file-content a:hover { text-decoration: underline; }
  .file-content img { max-width: 100%; border-radius: 8px; margin: 12px 0; }
  .placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); font-size: 13px; }
</style>
</head>
<body>
<aside class="sidebar">
  <div class="sidebar-header">
    <div class="logo" style="width:18px;height:18px;background:var(--accent);border-radius:4px;display:flex;align-items:center;justify-content:center;">
      <svg viewBox="0 0 24 24" fill="white" width="12" height="12"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
    </div>
    <span>raw/ 源文件</span>
  </div>
  <div class="sidebar-tree">"""

        for cat_name in sorted(categories.keys()):
            display_name = CATEGORY_NAMES.get(cat_name, cat_name)
            files = categories[cat_name]
            html += f'<div class="tree-cat"><div class="cat-header" onclick="this.nextElementSibling.classList.toggle(\'open\');this.querySelector(\'.cat-chevron\').classList.toggle(\'open\');"><span class="cat-chevron open"><svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg></span><span>{display_name}</span><span style="margin-left:auto;font-size:10px;color:var(--text-muted)">{len(files)}</span></div>'
            html += '<div class="cat-files open">'
            for fname in files:
                file_path = f"{cat_name}/{fname}" if cat_name != "_root" else fname
                html += f'<div class="file-item" onclick="loadFile(\'{file_path}\')" title="{fname}">{fname}</div>'
            html += '</div></div>'

        html += """</div>
</aside>
<div class="main">
  <div class="toolbar">
    <button class="toolbar-btn" onclick="history.back()" title="Back"><svg viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg></button>
    <div class="toolbar-title">原始文件浏览</div>
  </div>
  <div class="content" id="content"><div class="placeholder">选择一个文件查看内容</div></div>
</div>
<script src="https://cdn.jsdelivr.net/npm/marked@11/lib/marked.umd.min.js"></script>
<script>
function loadFile(path) {
  var el = document.getElementById('content');
  el.innerHTML = '<div class="placeholder">加载中...</div>';
  fetch('/raw-file/' + path).then(function(r) {
    if (!r.ok) throw new Error('Not found');
    return r.text();
  }).then(function(text) {
    // Strip frontmatter
    var m = text.match(/^---\\n[\\s\\S]*?\\n---\\n([\\s\\S]*)/);
    var body = m ? m[1] : text;
    el.innerHTML = '<div class="file-content">' + marked.parse(body) + '</div>';
  }).catch(function() {
    el.innerHTML = '<div class="placeholder">文件加载失败</div>';
  });
}
</script>
</body>
</html>"""
        return html

    def log_message(self, format, *args):
        sys.stderr.write(f"[KB] {args[0]}\n")


def main():
    parser = argparse.ArgumentParser(description="AI Knowledge Base Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), KBHandler)
    print(f"AI Knowledge Base running at http://localhost:{args.port}")
    print(f"Accessible on LAN at http://<your-ip>:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
