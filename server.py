#!/usr/bin/env python3
"""
Lightweight HTTP server for the AI Knowledge Base.
Serves markdown files with a clean, mobile-responsive UI.
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
RAW_DIR = KB_ROOT / "raw"
INDEX_FILE = KB_ROOT / "index.md"

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


def _resolve_wiki_link(key):
    """Resolve a wiki link key (filename stem or title) to a wiki URL path."""
    cache = _build_path_cache()
    rel = cache.get(key)
    if rel:
        return f"/wiki/{rel}"
    # Fallback: search by partial match on filename stem
    for stem, path in cache.items():
        if key.lower() in stem.lower() or stem.lower() in key.lower():
            return f"/wiki/{path}"
    return None


def render_markdown(text, source_path=""):
    """Minimal markdown-to-HTML converter."""
    _, body = parse_frontmatter(text)
    html = body

    # Wiki-style links [[name|display]] -- must come before standard links
    def replace_wiki_pipe(m):
        key, display = m.group(1).strip(), m.group(2)
        url = _resolve_wiki_link(key)
        if url:
            return f'<a href="{url}">{display}</a>'
        return display  # fallback: plain text

    html = re.sub(
        r"\[\[([^\]|]+)\|([^\]]+)\]\]",
        replace_wiki_pipe,
        html,
    )

    # Wiki-style links [[title]] without pipe -- match against frontmatter title
    def replace_wiki_title(m):
        title = m.group(1).strip()
        url = _resolve_wiki_link(title)
        if url:
            return f'<a href="{url}">{title}</a>'
        return title  # fallback: plain text

    html = re.sub(
        r"\[\[([^\]|]+)\]\]",
        replace_wiki_title,
        html,
    )

    # Code blocks
    html = re.sub(
        r"```(\w*)\n(.*?)```",
        r'<pre><code class="lang-\1">\2</code></pre>',
        html,
        flags=re.DOTALL,
    )

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Headers
    html = re.sub(r"^##### (.+)$", r"<h5>\1</h5>", html, flags=re.MULTILINE)
    html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Images
    html = re.sub(
        r"!\[([^\]]*)\]\(([^\)]+)\)",
        r'<img src="\2" alt="\1" loading="lazy">',
        html,
    )

    # Links (only after processing images to avoid conflicts)
    html = re.sub(
        r"\[([^\]]+)\]\(([^\)]+)\)",
        r'<a href="/wiki/\2">\1</a>',
        html,
    )

    # Tables
    lines = html.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" in line and i + 1 < len(lines) and re.match(r"^[\s|:-]+$", lines[i + 1]):
            result.append("<table>")
            # Header
            cells = [c.strip() for c in line.strip("|").split("|")]
            result.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr></thead>")
            i += 2  # skip separator
            result.append("<tbody>")
            while i < len(lines) and "|" in lines[i]:
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                if any(c for c in cells):
                    result.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
                i += 1
            result.append("</tbody></table>")
        else:
            # Paragraphs
            if line.strip():
                # Lists
                if re.match(r"^\s*[-*] ", line):
                    if not result or not result[-1].startswith("<ul>"):
                        result.append("<ul>")
                    content = re.sub(r"^\s*[-*] ", "", line)
                    result.append(f"<li>{content}</li>")
                    # Continue list
                    while i + 1 < len(lines) and re.match(r"^\s*[-*] ", lines[i + 1]):
                        i += 1
                        content = re.sub(r"^\s*[-*] ", "", lines[i])
                        result.append(f"<li>{content}</li>")
                    result.append("</ul>")
                elif re.match(r"^\s*\d+\. ", line):
                    if not result or not result[-1].startswith("<ol>"):
                        result.append("<ol>")
                    content = re.sub(r"^\s*\d+\. ", "", line)
                    result.append(f"<li>{content}</li>")
                    while i + 1 < len(lines) and re.match(r"^\s*\d+\. ", lines[i + 1]):
                        i += 1
                        content = re.sub(r"^\s*\d+\. ", "", lines[i])
                        result.append(f"<li>{content}</li>")
                    result.append("</ol>")
                else:
                    # Check if previous was list
                    if result and (result[-1] == "</ul>" or result[-1] == "</ol>"):
                        result.append(f"<p>{line}</p>")
                    else:
                        result.append(f"<p>{line}</p>")
            i += 1
    html = "\n".join(result)

    # Blockquotes
    html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r"^---+$", "<hr>", html, flags=re.MULTILINE)

    return html


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


class KBHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.index_cache = None
        super().__init__(*args, directory=str(KB_ROOT), **kwargs)

    def do_GET(self):
        path = unquote(self.path)

        if path == "/" or path == "/index.html":
            self.serve_home()
        elif path.startswith("/wiki/"):
            self.serve_wiki(path[len("/wiki/"):])
        elif path == "/api/index":
            self.serve_api_index()
        elif path == "/search":
            self.serve_search()
        else:
            super().do_GET()

    def serve_home(self):
        """Serve the home page with category navigation."""
        pages = build_index()
        categories = {}
        for path, info in pages.items():
            cat = info["category"]
            categories.setdefault(cat, []).append(info)

        cat_html = ""
        for cat_key in sorted(categories.keys()):
            cat_name = CATEGORY_NAMES.get(cat_key, cat_key.upper())
            items = categories[cat_key]
            cards = ""
            for item in items:
                tags_html = ""
                if item["tags"]:
                    tags = [t.strip() for t in item["tags"].split(",")]
                    tags_html = " ".join(
                        f'<span class="tag">{t}</span>' for t in tags
                    )
                cards += f"""
                <a href="/wiki/{item['path']}" class="card">
                    <h3>{item['title']}</h3>
                    <div class="card-meta">
                        {tags_html}
                    </div>
                </a>"""
            cat_html += f"""
            <section class="category">
                <h2>{cat_name}</h2>
                <div class="card-grid">{cards}</div>
            </section>"""

        total = len(pages)
        self.send_html(f"""
        <div class="home">
            <header class="hero">
                <h1>AI 知识库</h1>
                <p>自动驾驶标定与感知 · {total} 篇知识文档</p>
                <div class="search-bar">
                    <input type="text" id="searchInput" placeholder="搜索知识库..." onkeydown="if(event.key==='Enter')doSearch()">
                    <button onclick="doSearch()">搜索</button>
                </div>
            </header>
            <div id="searchResults" class="search-results" style="display:none"></div>
            <nav class="categories">
                {''.join(f'<a href="#{k}" class="cat-link">{CATEGORY_NAMES.get(k, k)}</a>' for k in sorted(categories.keys()))}
            </nav>
            {cat_html}
        </div>
        <script>
        function doSearch() {{
            const q = document.getElementById('searchInput').value.trim();
            if (!q) return;
            fetch('/api/index')
                .then(r => r.json())
                .then(data => {{
                    const results = data.filter(p =>
                        p.title.toLowerCase().includes(q.toLowerCase()) ||
                        p.tags.toLowerCase().includes(q.toLowerCase()) ||
                        p.category.toLowerCase().includes(q.toLowerCase()) ||
                        p.path.toLowerCase().includes(q.toLowerCase())
                    );
                    const el = document.getElementById('searchResults');
                    if (results.length === 0) {{
                        el.innerHTML = '<p>未找到相关结果</p>';
                    }} else {{
                        el.innerHTML = '<h3>搜索结果 (' + results.length + ')</h3>' +
                            results.map(r => '<a href="/wiki/' + r.path + '" class="card"><h3>' + r.title + '</h3></a>').join('');
                    }}
                    el.style.display = 'block';
                }});
        }}
        </script>
        """)

    def serve_wiki(self, rel_path):
        """Serve a wiki page as rendered HTML."""
        file_path = WIKI_DIR / rel_path
        if not file_path.exists():
            self.send_error(404, f"Wiki page not found: {rel_path}")
            return

        text = file_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        # Remove the leading title line from body since template renders title separately
        body_no_title = re.sub(r'^\n?# .+\n+', '', body, count=1)
        html_body = render_markdown(body_no_title)

        title = fm.get("title", file_path.stem)
        category = fm.get("category", "")
        cat_name = CATEGORY_NAMES.get(category, category)
        tags = fm.get("tags", "")
        tags_html = ""
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            tags_html = " ".join(f'<span class="tag">{t}</span>' for t in tag_list)

        self.send_html(f"""
        <article class="wiki-page">
            <nav class="breadcrumb">
                <a href="/">知识库</a>
                {f'› <a href="/?cat={category}">{cat_name}</a> ›' if category else '›'}
                <span>{title}</span>
            </nav>
            <h1>{title}</h1>
            {f'<div class="wiki-meta">{tags_html}</div>' if tags_html else ''}
            <div class="wiki-content">{html_body}</div>
        </article>
        """)

    def serve_api_index(self):
        """JSON API: return list of all wiki pages."""
        pages = list(build_index().values())
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(pages, ensure_ascii=False).encode())

    def serve_search(self):
        """Simple search page."""
        self.send_html("""
        <div class="home">
            <header class="hero">
                <h1>搜索知识库</h1>
                <div class="search-bar">
                    <input type="text" id="searchInput" placeholder="输入关键词..." autofocus onkeydown="if(event.key==='Enter')doSearch()">
                    <button onclick="doSearch()">搜索</button>
                </div>
            </header>
            <div id="searchResults" class="search-results"></div>
        </div>
        <script>
        function doSearch() {
            const q = document.getElementById('searchInput').value.trim();
            if (!q) return;
            fetch('/api/index')
                .then(r => r.json())
                .then(data => {
                    const results = data.filter(p =>
                        p.title.toLowerCase().includes(q.toLowerCase()) ||
                        p.tags.toLowerCase().includes(q.toLowerCase()) ||
                        p.category.toLowerCase().includes(q.toLowerCase()) ||
                        p.path.toLowerCase().includes(q.toLowerCase())
                    );
                    const el = document.getElementById('searchResults');
                    if (results.length === 0) {
                        el.innerHTML = '<p>未找到相关结果</p>';
                    } else {
                        el.innerHTML = '<h3>搜索结果 (' + results.length + ')</h3>' +
                            results.map(r => '<a href="/wiki/' + r.path + '" class="card"><h3>' + r.title + '</h3></a>').join('');
                    }
                });
        }
        </script>
        """)

    def send_html(self, body):
        """Send a complete HTML page — cyberpunk themed."""
        content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 知识库</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root {{
    --void: #050810;
    --deep: #0a0f1e;
    --panel: #0c1222;
    --panel-bright: #111b30;
    --cyan: #00ff41;
    --cyan-dim: #00cc33;
    --cyan-glow: rgba(0, 255, 65, 0.15);
    --cyan-bright: #00ffaa;
    --magenta: #ff0080;
    --magenta-glow: rgba(255, 0, 128, 0.12);
    --blue: #00d4ff;
    --blue-glow: rgba(0, 212, 255, 0.1);
    --amber: #ffbe0b;
    --amber-glow: rgba(255, 190, 11, 0.1);
    --text: #c8d6e5;
    --text-bright: #f0f4f8;
    --text-dim: #5a6a80;
    --border: #1a2744;
    --border-bright: #2a4068;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
    font-family: "Share Tech Mono", "Noto Sans SC", monospace;
    background: var(--void);
    color: var(--text);
    line-height: 1.7;
    font-size: 15px;
    overflow-x: hidden;
}}

/* Grid background */
body::before {{
    content: "";
    position: fixed;
    inset: 0;
    background:
        linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}}

/* Scanline overlay */
body::after {{
    content: "";
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 0, 0, 0.08) 2px,
        rgba(0, 0, 0, 0.08) 4px
    );
    pointer-events: none;
    z-index: 9999;
}}

a {{ color: var(--cyan); text-decoration: none; transition: all 0.2s; }}
a:hover {{ color: var(--cyan-bright); text-shadow: 0 0 8px var(--cyan-glow); }}

/* Top bar */
.topbar {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--magenta), var(--cyan), var(--blue));
    z-index: 100;
    animation: barPulse 4s ease-in-out infinite;
}}
@keyframes barPulse {{
    0%, 100% {{ opacity: 0.8; }}
    50% {{ opacity: 1; }}
}}

/* Hero */
.home {{ position: relative; z-index: 1; }}
.hero {{
    text-align: center;
    padding: 4rem 1.5rem 2.5rem;
    position: relative;
}}
.hero::after {{
    content: "";
    position: absolute;
    bottom: 0;
    left: 10%;
    right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--cyan-dim), transparent);
}}
.hero h1 {{
    font-family: "Orbitron", "Noto Sans SC", sans-serif;
    font-size: 2.8rem;
    font-weight: 900;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
    color: var(--cyan);
    text-shadow:
        0 0 10px rgba(0, 255, 65, 0.5),
        0 0 40px rgba(0, 255, 65, 0.15);
    animation: textFlicker 8s infinite;
}}
@keyframes textFlicker {{
    0%, 95%, 100% {{ opacity: 1; }}
    96% {{ opacity: 0.85; }}
    97% {{ opacity: 1; }}
    98% {{ opacity: 0.9; }}
}}
.hero p {{
    color: var(--text-dim);
    font-size: 0.9rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}}
.hero p::before, .hero p::after {{ content: "// "; color: var(--magenta); }}

/* Status indicator */
.status {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
    color: var(--cyan-dim);
    margin-top: 0.8rem;
    letter-spacing: 0.1em;
}}
.status::before {{
    content: "";
    width: 6px;
    height: 6px;
    background: var(--cyan);
    border-radius: 50%;
    box-shadow: 0 0 6px var(--cyan);
    animation: blink 2s infinite;
}}
@keyframes blink {{
    0%, 49% {{ opacity: 1; }}
    50%, 100% {{ opacity: 0.2; }}
}}

/* Search */
.search-bar {{
    display: flex;
    max-width: 520px;
    margin: 2rem auto 0;
    gap: 0;
}}
.search-bar input {{
    flex: 1;
    padding: 0.75rem 1rem;
    border: 1px solid var(--border-bright);
    border-right: none;
    background: var(--panel);
    color: var(--text-bright);
    font-family: "Share Tech Mono", monospace;
    font-size: 0.9rem;
    outline: none;
    caret-color: var(--cyan);
}}
.search-bar input::placeholder {{ color: var(--text-dim); }}
.search-bar input:focus {{
    border-color: var(--cyan);
    box-shadow: 0 0 12px var(--cyan-glow), inset 0 0 12px var(--cyan-glow);
}}
.search-bar button {{
    padding: 0.75rem 1.5rem;
    border: 1px solid var(--cyan);
    background: var(--cyan-glow);
    color: var(--cyan);
    font-family: "Orbitron", sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    cursor: pointer;
    transition: all 0.2s;
    text-transform: uppercase;
}}
.search-bar button:hover {{
    background: var(--cyan);
    color: var(--void);
    box-shadow: 0 0 20px var(--cyan-glow);
}}

/* Category nav */
.categories {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 1.5rem 1.5rem;
    position: sticky;
    top: 0;
    background: rgba(5, 8, 16, 0.92);
    backdrop-filter: blur(10px);
    z-index: 10;
    border-bottom: 1px solid var(--border);
}}
.cat-link {{
    padding: 0.35rem 0.9rem;
    border: 1px solid var(--border);
    font-family: "Share Tech Mono", monospace;
    font-size: 0.75rem;
    color: var(--text-dim);
    transition: all 0.2s;
    letter-spacing: 0.08em;
    position: relative;
    clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px));
}}
.cat-link::before {{
    content: "> ";
    color: var(--magenta);
    opacity: 0;
    transition: opacity 0.2s;
}}
.cat-link:hover {{
    border-color: var(--cyan);
    color: var(--cyan);
    text-decoration: none;
    background: var(--cyan-glow);
}}
.cat-link:hover::before {{ opacity: 1; }}

/* Sections */
.category {{
    padding: 2rem 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
    position: relative;
}}
.category h2 {{
    font-family: "Orbitron", "Noto Sans SC", sans-serif;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 1.2rem;
    padding-bottom: 0.5rem;
    color: var(--blue);
    text-shadow: 0 0 8px var(--blue-glow);
    border-bottom: 1px solid var(--border);
    position: relative;
}}
.category h2::after {{
    content: "";
    position: absolute;
    bottom: -1px;
    left: 0;
    width: 60px;
    height: 1px;
    background: var(--blue);
    box-shadow: 0 0 8px var(--blue);
}}

/* Cards */
.card-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
}}
.card {{
    display: block;
    padding: 1.2rem;
    background: var(--panel);
    border: 1px solid var(--border);
    position: relative;
    transition: all 0.25s;
    clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px));
}}
.card::before {{
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    background: var(--cyan);
    opacity: 0;
    transition: opacity 0.25s;
    box-shadow: 0 0 8px var(--cyan);
}}
.card::after {{
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, var(--cyan), transparent);
    opacity: 0;
    transition: opacity 0.25s;
}}
.card:hover {{
    border-color: var(--cyan-dim);
    transform: translateX(2px);
    text-decoration: none;
    background: var(--panel-bright);
}}
.card:hover::before, .card:hover::after {{ opacity: 1; }}
.card h3 {{
    font-size: 0.95rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
    color: var(--text-bright);
    transition: color 0.2s;
}}
.card:hover h3 {{ color: var(--cyan); }}
.card-meta {{ display: flex; flex-wrap: wrap; gap: 0.3rem; }}

/* Tags */
.tag {{
    display: inline-block;
    padding: 0.15rem 0.5rem;
    font-size: 0.7rem;
    background: var(--magenta-glow);
    border: 1px solid rgba(255, 0, 128, 0.2);
    color: var(--magenta);
    font-family: "Share Tech Mono", monospace;
    letter-spacing: 0.05em;
}}

/* Wiki page */
.wiki-page {{
    max-width: 820px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    position: relative;
    z-index: 1;
}}
.breadcrumb {{
    font-family: "Share Tech Mono", monospace;
    font-size: 0.8rem;
    color: var(--text-dim);
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
    letter-spacing: 0.05em;
}}
.breadcrumb a {{ color: var(--blue); }}
.breadcrumb a:hover {{ text-shadow: 0 0 6px var(--blue-glow); }}
.wiki-page h1 {{
    font-family: "Orbitron", "Noto Sans SC", sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--cyan);
    text-shadow: 0 0 10px var(--cyan-glow);
    margin-bottom: 0.5rem;
}}
.wiki-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-bottom: 2.5rem;
}}
.wiki-content {{ position: relative; z-index: 1; }}
.wiki-content h2 {{
    font-family: "Orbitron", "Noto Sans SC", sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    margin: 2.5rem 0 1rem;
    padding-bottom: 0.5rem;
    color: var(--blue);
    border-bottom: 1px solid var(--border);
    text-shadow: 0 0 6px var(--blue-glow);
}}
.wiki-content h3 {{
    font-size: 1.1rem;
    font-weight: 700;
    margin: 1.5rem 0 0.8rem;
    color: var(--text-bright);
    border-left: 2px solid var(--magenta);
    padding-left: 0.8rem;
}}
.wiki-content h4 {{
    font-size: 1rem;
    margin: 1.2rem 0 0.6rem;
    color: var(--text-bright);
}}
.wiki-content p {{ margin: 0.8rem 0; color: var(--text); }}
.wiki-content ul, .wiki-content ol {{ margin: 0.8rem 0; padding-left: 1.5rem; }}
.wiki-content li {{ margin: 0.3rem 0; color: var(--text); }}
.wiki-content li::marker {{ color: var(--cyan); }}
.wiki-content code {{
    background: var(--panel);
    padding: 0.15rem 0.4rem;
    border: 1px solid var(--border);
    color: var(--cyan);
    font-family: "Share Tech Mono", monospace;
    font-size: 0.85em;
}}
.wiki-content pre {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 2px solid var(--cyan);
    padding: 1rem;
    overflow-x: auto;
    margin: 1rem 0;
    position: relative;
}}
.wiki-content pre::before {{
    content: attr(data-lang, "code");
    position: absolute;
    top: -8px;
    right: 8px;
    background: var(--cyan);
    color: var(--void);
    font-size: 0.6rem;
    padding: 0 0.4rem;
    font-family: "Share Tech Mono", monospace;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}
.wiki-content pre code {{
    background: none;
    border: none;
    padding: 0;
    font-size: 0.85rem;
    line-height: 1.6;
    color: var(--text);
}}
.wiki-content table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    font-size: 0.85rem;
}}
.wiki-content th, .wiki-content td {{
    padding: 0.6rem 0.8rem;
    border: 1px solid var(--border);
    text-align: left;
}}
.wiki-content th {{
    background: var(--panel-bright);
    color: var(--blue);
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-size: 0.8rem;
}}
.wiki-content blockquote {{
    border-left: 2px solid var(--magenta);
    padding: 0.8rem 1rem;
    margin: 1rem 0;
    color: var(--text-dim);
    background: var(--magenta-glow);
}}
.wiki-content hr {{
    border: none;
    height: 1px;
    background: linear-gradient(90deg, var(--border), var(--border-bright), var(--border));
    margin: 2rem 0;
}}
.wiki-content img {{
    max-width: 100%;
    border: 1px solid var(--border);
    margin: 1rem 0;
}}

/* Search results */
.search-results {{
    max-width: 800px;
    margin: 1.5rem auto;
    padding: 0 1.5rem;
    position: relative;
    z-index: 1;
}}
.search-results h3 {{
    font-family: "Orbitron", sans-serif;
    color: var(--cyan);
    font-size: 0.9rem;
    letter-spacing: 0.1em;
    margin-bottom: 1rem;
}}
.search-results .card {{ margin-bottom: 0.5rem; }}
.search-results p {{
    color: var(--text-dim);
    font-family: "Share Tech Mono", monospace;
    padding: 1rem;
    border: 1px dashed var(--border);
    background: var(--panel);
}}
.search-results p::before {{ content: "ERROR: "; color: var(--magenta); }}

/* Responsive */
@media (max-width: 640px) {{
    .hero {{ padding: 3rem 1rem 1.5rem; }}
    .hero h1 {{ font-size: 1.8rem; }}
    .hero p {{ font-size: 0.8rem; }}
    .card-grid {{ grid-template-columns: 1fr; }}
    .wiki-page {{ padding: 1rem; }}
    .wiki-page h1 {{ font-size: 1.4rem; }}
    .categories {{ padding: 0.8rem 1rem; }}
    .category {{ padding: 1rem; }}
    .search-bar {{ margin: 1rem auto 0; }}
    .wiki-content table {{ font-size: 0.75rem; }}
    .wiki-content pre {{ padding: 0.8rem; font-size: 0.8rem; }}
}}
</style>
</head>
<body>
<div class="topbar"></div>
{body}
<script>
document.querySelectorAll('.wiki-content pre').forEach(pre => {{
  const code = pre.querySelector('code');
  const cls = code ? code.className : '';
  const m = cls.match(/lang-(\\w+)/);
  pre.setAttribute('data-lang', m ? m[1] : 'code');
}});
</script>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

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
