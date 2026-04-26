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
import hmac
import jwt
import hashlib
import secrets
import time
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


# JWT authentication
# NOTE: Secret is regenerated on server restart — all tokens expire on restart
JWT_SECRET = secrets.token_hex(32)
TOKEN_EXPIRY = 24 * 3600  # 24 hours in seconds


def hash_password(password: str) -> str:
    """Hash password with random salt using SHA-256."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"sha256:{salt}:{pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    parts = stored_hash.split(":")
    if len(parts) != 3 or parts[0] != "sha256":
        return False
    salt = parts[1]
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return hmac.compare_digest(pwd_hash, parts[2])


def generate_token(username: str) -> str:
    """Generate JWT token for authenticated user."""
    payload = {
        "sub": username,
        "exp": int(time.time()) + TOKEN_EXPIRY,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict | None:
    """Verify and decode JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# User database: {phone_number: {"password_hash": "sha256:salt:hash"}}
USERS = {
    "18352869670": {
        "password_hash": hash_password("yuange666"),
    }
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

        # Unprotected routes
        if path == "/login" or path == "/login.html":
            self.serve_login_page()
            return

        # All other routes require authentication
        if not self._require_auth():
            return

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
        elif path == "/api/auth/verify":
            self.handle_verify()
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
        """Generate an Obsidian-themed raw file browser page."""
        raw_dir = KB_ROOT / "raw"
        if not raw_dir.exists():
            return "<p>raw/ directory not found</p>"

        categories = {}
        for item in sorted(raw_dir.iterdir()):
            if item.is_dir():
                files = sorted([f.name for f in item.iterdir() if f.suffix == ".md"])
                if files:
                    categories[item.name] = files
            elif item.suffix == ".md":
                categories.setdefault("_root", []).append(item.name)

        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>原始文件浏览 — AI 知识库</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg-primary: #ffffff; --bg-secondary: #f6f7f8; --bg-tertiary: #ececec;
  --bg-hover: #e8eaed; --bg-active: #e4e6eb; --bg-code: #f0f2f5;
  --text-primary: #1a1a1a; --text-secondary: #4a4a4a; --text-tertiary: #6b7280;
  --text-link: #5b6abf; --text-link-hover: #3d4fa0;
  --border-color: #e2e4e8; --border-light: #f0f0f0;
  --accent: #5b6abf; --accent-light: rgba(91,106,191,0.08);
  --sidebar-width: 260px; --content-max-width: 820px;
  --font-sans: "Noto Sans SC", -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: "SF Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--font-sans); background: var(--bg-primary); color: var(--text-primary); font-size: 15px; line-height: 1.75; overflow: hidden; height: 100vh; display: flex; -webkit-font-smoothing: antialiased; }

/* Sidebar */
.sidebar { width: var(--sidebar-width); min-width: var(--sidebar-width); height: 100vh; background: var(--bg-secondary); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; overflow: hidden; }
.sidebar-header { padding: 1rem 1rem 0.5rem; }
.sidebar-header a { color: var(--text-primary); font-weight: 600; font-size: 0.95rem; text-decoration: none; }
.sidebar-tree { flex: 1; overflow-y: auto; padding: 0 0.5rem; }
.sidebar-tree::-webkit-scrollbar { width: 4px; }
.sidebar-tree::-webkit-scrollbar-thumb { background: #ddd; border-radius: 2px; }
.cat-header { display: flex; align-items: center; padding: 0.8rem 0.5rem 0.3rem; cursor: pointer; font-size: 0.72rem; font-weight: 600; color: var(--text-tertiary); letter-spacing: 0.06em; text-transform: uppercase; gap: 4px; user-select: none; transition: color 0.15s; }
.cat-header:hover { color: var(--text-primary); }
.cat-chevron { width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; transition: transform 0.15s; flex-shrink: 0; }
.cat-chevron.open { transform: rotate(90deg); }
.cat-chevron svg { width: 10px; height: 10px; fill: var(--text-tertiary); }
.cat-files { overflow: hidden; max-height: 0; transition: max-height 0.2s; }
.cat-files.open { max-height: 2000px; }
.file-item { padding: 0.2rem 0.4rem; font-size: 13px; color: var(--text-secondary); cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-radius: 4px; margin-left: 0.6rem; transition: all 0.1s; }
.file-item:hover { color: var(--text-primary); background: var(--bg-hover); }
.file-item.active { color: var(--text-primary); background: var(--bg-active); font-weight: 500; }

/* Main area */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }

/* Page header (left side, like wiki) */
.page-header { position: absolute; top: 0; left: 0; width: 140px; padding: 1.5rem 1rem 1.5rem 1.2rem; z-index: 5; display: none; flex-direction: column; }
.page-header.active { display: flex; }
.ph-breadcrumb { display: flex; align-items: center; gap: 0.25rem; font-size: 11px; color: var(--text-tertiary); margin-bottom: 0.6rem; }
.ph-breadcrumb a { color: var(--text-tertiary); text-decoration: none; }
.ph-breadcrumb a:hover { color: var(--accent); }
.ph-breadcrumb .sep { color: var(--border-color); }
.ph-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); line-height: 1.3; }

/* Content */
.content { flex: 1; overflow-y: auto; padding: 1.5rem 2.5rem 3rem 2.5rem; }
.content::-webkit-scrollbar { width: 6px; }
.content::-webkit-scrollbar-thumb { background: #ddd; border-radius: 3px; }
.file-content { max-width: var(--content-max-width); margin: 0 auto; }

/* Markdown styles (matching wiki theme) */
.file-content h1 { display: none; }
.file-content h2 { font-size: 1.25rem; font-weight: 600; margin: 2rem 0 0.8rem; color: var(--text-primary); }
.file-content h3 { font-size: 1.05rem; font-weight: 600; margin: 1.5rem 0 0.6rem; color: var(--text-primary); }
.file-content h4 { font-size: 0.95rem; font-weight: 600; margin: 1.2rem 0 0.5rem; color: var(--text-primary); }
.file-content p { margin: 0.6rem 0; color: var(--text-primary); }
.file-content ul, .file-content ol { margin: 0.5rem 0; padding-left: 1.5rem; }
.file-content li { margin: 0.2rem 0; color: var(--text-primary); }
.file-content li::marker { color: var(--text-tertiary); }
.file-content hr { border: none; height: 1px; background: var(--border-color); margin: 2rem 0; }
.file-content code { background: var(--bg-code); border: 1px solid var(--border-light); color: #d6336c; font-family: var(--font-mono); font-size: 0.85em; padding: 0.1rem 0.35rem; border-radius: 4px; }
.file-content pre { background: var(--bg-secondary); border: 1px solid var(--border-color); border-left: 3px solid var(--accent); padding: 1rem 1.2rem; margin: 1rem 0; border-radius: 6px; position: relative; overflow-x: auto; }
.file-content pre code { background: none; border: none; padding: 0; font-size: 0.85rem; line-height: 1.6; color: var(--text-primary); }
.file-content blockquote { border-left: 3px solid var(--accent); padding: 0.6rem 1rem; margin: 1rem 0; color: var(--text-secondary); background: var(--accent-light); border-radius: 0 4px 4px 0; }
.file-content table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.88rem; }
.file-content th, .file-content td { padding: 0.5rem 0.8rem; border: 1px solid var(--border-color); text-align: left; }
.file-content th { background: var(--bg-secondary); color: var(--text-primary); font-weight: 600; font-size: 0.82rem; }
.file-content a { color: var(--text-link); text-decoration: none; }
.file-content a:hover { color: var(--text-link-hover); }
.file-content img { max-width: 100%; border: 1px solid var(--border-color); border-radius: 6px; margin: 1rem 0; }

.placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary); font-size: 13px; }
.back-link { display: inline-flex; align-items: center; gap: 4px; color: var(--text-tertiary); text-decoration: none; font-size: 13px; padding: 4px 8px; border-radius: 4px; margin-bottom: 8px; }
.back-link:hover { color: var(--text-primary); background: var(--bg-hover); }
</style>
</head>
<body>
<aside class="sidebar">
  <div class="sidebar-header"><a href="/">AI 知识库</a></div>
  <div class="sidebar-tree">"""

        for cat_name in sorted(categories.keys()):
            display_name = CATEGORY_NAMES.get(cat_name, cat_name)
            files = categories[cat_name]
            html += f'<div class="tree-cat"><div class="cat-header" onclick="this.nextElementSibling.classList.toggle(\'open\');this.querySelector(\'.cat-chevron\').classList.toggle(\'open\');"><span class="cat-chevron open"><svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg></span><span>{display_name}</span><span style="margin-left:auto;font-size:10px;color:var(--text-tertiary)">{len(files)}</span></div>'
            html += '<div class="cat-files open">'
            for fname in files:
                file_path = f"{cat_name}/{fname}" if cat_name != "_root" else fname
                html += f'<div class="file-item" data-path="{file_path}" onclick="loadFile(\'{file_path}\',this)" title="{fname}">{fname}</div>'
            html += '</div></div>'

        html += """</div>
</aside>
<div class="main">
  <div class="page-header" id="pageHeader"></div>
  <div class="content" id="content"><div class="placeholder">选择一个文件查看内容</div></div>
</div>
<script src="https://cdn.jsdelivr.net/npm/marked@11/lib/marked.umd.min.js"></script>
<script>
function loadFile(path, el) {
  // Highlight active file
  document.querySelectorAll('.file-item').forEach(function(i) { i.classList.remove('active'); });
  if (el) el.classList.add('active');

  var contentEl = document.getElementById('content');
  var headerEl = document.getElementById('pageHeader');
  contentEl.innerHTML = '<div class="placeholder">加载中...</div>';

  fetch('/raw-file/' + path).then(function(r) {
    if (!r.ok) throw new Error('Not found');
    return r.text();
  }).then(function(text) {
    // Parse frontmatter for title
    var title = '';
    var body = text;
    var m = text.match(/^---\\n([\\s\\S]*?)\\n---\\n([\\s\\S]*)/);
    if (m) {
      var fmLines = m[1].split('\\n');
      for (var i = 0; i < fmLines.length; i++) {
        var ci = fmLines[i].indexOf(':');
        if (ci > 0 && fmLines[i].substring(0, ci).trim() === 'title') {
          title = fmLines[i].substring(ci + 1).trim();
        }
      }
      body = m[2];
    }

    // Set page header
    var parts = path.split('/');
    var breadcrumbHtml = '<a href="/">wiki</a>';
    for (var j = 0; j < parts.length; j++) {
      breadcrumbHtml += '<span class="sep">/</span><span>' + parts[j].replace(/\\.md$/, '') + '</span>';
    }
    var headerHtml = '<div class="ph-breadcrumb">' + breadcrumbHtml + '</div>';
    if (title) headerHtml += '<div class="ph-title">' + title + '</div>';
    headerEl.innerHTML = headerHtml;
    headerEl.classList.add('active');

    contentEl.innerHTML = '<div class="file-content">' + marked.parse(body) + '</div>';
  }).catch(function() {
    contentEl.innerHTML = '<div class="placeholder">文件加载失败</div>';
    headerEl.innerHTML = '';
    headerEl.classList.remove('active');
  });
}
</script>
</body>
</html>"""
        return html

    def do_POST(self):
        """Handle POST requests — auth endpoints."""
        path = unquote(unquote(self.path))
        path = path.split("?")[0]
        if path.startswith("//"):
            path = path[1:]

        if path == "/api/auth/login":
            self.handle_login()
        else:
            self.send_error(405, "Method not allowed")

    def handle_login(self):
        """POST /api/auth/login — authenticate user and return JWT."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return self._send_json({"success": False, "message": "无效的请求体"}, 400)

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return self._send_json({"success": False, "message": "请填写账号和密码"}, 400)

        # Look up user by phone number (username field)
        user = USERS.get(username)
        if not user or not verify_password(password, user["password_hash"]):
            return self._send_json({"success": False, "message": "账号或密码错误"}, 401)

        token = generate_token(username)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", f"kb_token={token}; Path=/; HttpOnly; Max-Age={TOKEN_EXPIRY}")
        body = json.dumps({
            "success": True,
            "message": "登录成功",
            "token": token,
        }, ensure_ascii=False).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_verify(self):
        """GET /api/auth/verify — validate current token."""
        token = self._get_auth_token()
        if not token:
            return self._send_json({"valid": False, "message": "未提供认证令牌"}, 401)

        payload = verify_token(token)
        if not payload:
            return self._send_json({"valid": False, "message": "令牌无效或已过期"}, 401)

        return self._send_json({"valid": True, "user": payload.get("sub", "")})

    def serve_login_page(self):
        """GET /login — serve the login HTML page."""
        login_path = PUBLIC_DIR / "login.html"
        if not login_path.exists():
            self.send_error(404, "login.html not found")
            return
        self._serve_file(login_path, "text/html; charset=utf-8")

    def _get_auth_token(self):
        """Extract Bearer token from Authorization header or cookie."""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        # Fall back to cookie
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("kb_token="):
                return part[len("kb_token="):]
        return None

    def _require_auth(self):
        """Check authentication. Returns True if valid, sends redirect/401 if not."""
        token = self._get_auth_token()
        if not token or not verify_token(token):
            self._handle_unauthorized()
            return False
        return True

    def _handle_unauthorized(self):
        """Redirect to login page for HTML requests, or return 401 for API requests."""
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            self._send_json({"success": False, "message": "未提供认证令牌或令牌已过期"}, 401)
        else:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _send_json(self, data, status=200):
        """Send a JSON response."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
