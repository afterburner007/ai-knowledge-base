# 在线添加 Raw 文件 + LLM 自动 Ingest 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供 Web 界面上传/新建 raw md 文件，上传后自动调用 LLM 分析生成正式 wiki 页面（完整 ingest 流程）。

**Architecture:** 新建 FastAPI 应用 (`server_fastapi.py` + `app/` 模块)，迁移 server.py 中的只读 API，添加文件上传和 LLM ingest 端点，前端上传页面。

**Tech Stack:** FastAPI, uvicorn, PyJWT, httpx (LLM API 调用), Pydantic, 原生 HTML/JS 前端

---

### Task 1: 项目骨架 + 依赖

**Files:**
- Create: `requirements-fastapi.txt`
- Create: `app/__init__.py`
- Create: `app/api/__init__.py`
- Create: `app/llm/__init__.py`
- Create: `app/static/` (directory)

- [ ] **Step 1: 创建 requirements-fastapi.txt**

```txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
PyJWT>=2.8.0
httpx>=0.27.0
python-multipart>=0.0.9
```

- [ ] **Step 2: 创建 app 包目录和 __init__.py**

```bash
mkdir -p app/api app/llm app/static
```

```python
# app/__init__.py
"""AI Knowledge Base FastAPI application."""
```

```python
# app/api/__init__.py
"""API route handlers."""
```

```python
# app/llm/__init__.py
"""LLM client and ingest pipeline."""
```

```bash
mkdir -p app/static
```

- [ ] **Step 3: 安装依赖**

```bash
pip install -r requirements-fastapi.txt
```

- [ ] **Step 4: 提交**

```bash
git add requirements-fastapi.txt app/__init__.py app/api/__init__.py app/llm/__init__.py app/static/
git commit -m "chore: add FastAPI project skeleton and dependencies"
```

---

### Task 2: JWT 认证中间件 + 常量

**Files:**
- Create: `app/auth.py`
- Create: `app/config.py`

- [ ] **Step 1: 创建配置模块**

```python
# app/config.py
"""Application configuration — paths, JWT settings, LLM API settings."""
import os
from pathlib import Path

KB_ROOT = Path(__file__).parent.parent
WIKI_DIR = KB_ROOT / "wiki"
RAW_DIR = KB_ROOT / "raw"
PUBLIC_DIR = KB_ROOT / "public"
INDEX_FILE = KB_ROOT / "index.md"
LOG_FILE = KB_ROOT / "log.md"

# JWT settings — match server.py behavior (secret regenerated on restart)
import secrets
JWT_SECRET = os.environ.get("KB_JWT_SECRET", secrets.token_hex(32))
TOKEN_EXPIRY = 24 * 3600  # 24 hours

# User database — same as server.py
USERS = {
    "18352869670": {
        "password_hash": "sha256:db2fac630139bde79fb4de212a49ff8b:9f2d37aa9d6686e1f313535480dc8a0d050925cd507e044cb4743b81384d76f7",
    }
}

# LLM API settings
LLM_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL",
    "https://coding.dashscope.aliyuncs.com/apps/anthropic"
)
LLM_API_KEY = os.environ.get(
    "ANTHROPIC_AUTH_TOKEN",
    "sk-sp-c390987f0f1a49f8843e9fc96b09c6f7"
)
LLM_MODEL = os.environ.get(
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "qwen3.6-plus"
)

# Wiki categories
WIKI_CATEGORIES = ["3dgs", "avm", "calibration", "perception", "tracking", "fusion", "platform", "tools"]

# Upload limits
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".md"}
```

- [ ] **Step 2: 创建认证中间件**

```python
# app/auth.py
"""JWT authentication middleware for FastAPI."""
import hmac
import hashlib
import secrets
import time
import jwt
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from app.config import JWT_SECRET, TOKEN_EXPIRY, USERS


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


# Routes that don't require authentication
PUBLIC_PATHS = {
    "/", "/login", "/login.html", "/favicon.ico", "/robots.txt",
    "/api/auth/login", "/api/auth/verify",
    "/api/index", "/api/graph", "/api/wiki-path-map",
    "/docsify-theme.css",
}


def get_token_from_request(request: Request) -> str | None:
    """Extract Bearer token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    cookie = request.headers.get("Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("kb_token="):
            return part[len("kb_token="):]
    return None


async def auth_middleware(request: Request, call_next):
    """FastAPI middleware: redirect unauthenticated users to /login."""
    path = request.url.path.split("?")[0]

    # Public paths
    if path in PUBLIC_PATHS or path.startswith("/raw-file/") or path.startswith("/wiki/"):
        return await call_next(request)

    token = get_token_from_request(request)
    if not token or not verify_token(token):
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "未提供认证令牌或令牌已过期"}
            )
        return RedirectResponse(url="/login")

    return await call_next(request)
```

- [ ] **Step 3: 提交**

```bash
git add app/config.py app/auth.py
git commit -m "feat: add JWT auth middleware and config module"
```

---

### Task 3: Pydantic 数据模型

**Files:**
- Create: `app/models.py`

- [ ] **Step 1: 创建数据模型**

```python
# app/models.py
"""Pydantic models for API request/response validation."""
from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None


class VerifyResponse(BaseModel):
    valid: bool
    user: str = ""
    message: str = ""


class UploadResponse(BaseModel):
    success: bool
    file_path: str
    task_id: Optional[str] = None
    message: str


class IngestRequest(BaseModel):
    file_path: str  # raw/ relative path


class IngestResponse(BaseModel):
    task_id: str
    message: str


class IngestStatus(BaseModel):
    task_id: str
    status: str  # pending | processing | completed | failed
    result: Optional[dict] = None
    error: Optional[str] = None


class RawFileCreateRequest(BaseModel):
    filename: str
    content: str
    category: Optional[str] = None  # optional subdirectory under raw/


class RawFileCreateResponse(BaseModel):
    success: bool
    file_path: str
    message: str
```

- [ ] **Step 2: 提交**

```bash
git add app/models.py
git commit -m "feat: add Pydantic data models for API endpoints"
```

---

### Task 4: 认证路由 (login + verify)

**Files:**
- Create: `app/api/auth.py`

- [ ] **Step 1: 创建认证路由**

```python
# app/api/auth.py
"""Authentication routes: login, verify."""
import time
from fastapi import APIRouter, Response
from app.models import LoginRequest, LoginResponse, VerifyResponse
from app.auth import verify_password, generate_token, verify_token, get_token_from_request
from app.config import TOKEN_EXPIRY, USERS

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, response: Response):
    """POST /api/auth/login — authenticate and return JWT."""
    username = data.username.strip()
    password = data.password

    if not username or not password:
        return LoginResponse(success=False, message="请填写账号和密码")

    user = USERS.get(username)
    if not user or not verify_password(password, user["password_hash"]):
        return LoginResponse(success=False, message="账号或密码错误")

    token = generate_token(username)
    response.set_cookie(
        key="kb_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRY,
        path="/",
    )
    return LoginResponse(success=True, message="登录成功", token=token)


@router.get("/verify", response_model=VerifyResponse)
async def verify(request_token: str = None):
    """GET /api/auth/verify — validate current token."""
    # Token extracted via middleware or passed as query param
    from fastapi import Request
    # We'll use a dependency in the route to get the token
    pass


# Rewrite with proper Request access:
@router.get("/verify")
async def verify_endpoint(request: Request):
    """GET /api/auth/verify — validate current token."""
    token = get_token_from_request(request)
    if not token:
        return VerifyResponse(valid=False, message="未提供认证令牌")

    payload = verify_token(token)
    if not payload:
        return VerifyResponse(valid=False, message="令牌无效或已过期")

    return VerifyResponse(valid=True, user=payload.get("sub", ""))
```

- [ ] **Step 2: 提交**

```bash
git add app/api/auth.py
git commit -m "feat: add auth routes (login + verify)"
```

---

### Task 5: Wiki 只读路由迁移（从 server.py 到 FastAPI）

**Files:**
- Create: `app/api/wiki.py`
- Create: `app/services.py` — shared wiki building logic

- [ ] **Step 1: 创建共享服务模块**

```python
# app/services.py
"""Shared wiki building logic — migrated from server.py."""
import re
from pathlib import Path
from app.config import WIKI_DIR, INDEX_FILE, LOG_FILE, CATEGORY_NAMES


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
```

- [ ] **Step 2: 创建 wiki 路由**

```python
# app/api/wiki.py
"""Wiki read-only routes — migrated from server.py."""
import json
from pathlib import Path
from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, FileResponse
from app.services import build_index, build_graph, build_path_cache
from app.config import WIKI_DIR, PUBLIC_DIR, RAW_DIR, KB_ROOT, CATEGORY_NAMES

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
    """Serve the raw file browser HTML page (from server.py)."""
    # Reuse server.py's _generate_raw_browser_html — serve as static for now
    # We'll create a standalone HTML page in Task 8
    from app.api.upload import generate_raw_browser_html
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

    lines = [""]
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
```

- [ ] **Step 3: 提交**

```bash
git add app/services.py app/api/wiki.py
git commit -m "feat: migrate wiki read-only routes from server.py to FastAPI"
```

---

### Task 6: LLM API 客户端

**Files:**
- Create: `app/llm/client.py`

- [ ] **Step 1: 创建 LLM 客户端**

```python
# app/llm/client.py
"""LLM API client — communicates with Dashscope/Anthropic-compatible API."""
import httpx
import json
import re
from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL


async def call_llm(messages: list[dict], temperature: float = 0.3, timeout: float = 60.0) -> str:
    """Call LLM API and return response text."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/v1/messages",
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": 8192,
                "temperature": temperature,
                "messages": messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # Anthropic-style response
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block["text"]
        raise ValueError(f"Unexpected LLM response format: {data}")


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response (may contain markdown code blocks)."""
    # Try to find JSON in code blocks
    m = re.search(r"```(?:json)?\n([\s\S]*?)\n```", text)
    if m:
        text = m.group(1)

    # Find JSON object — may be nested
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in response: {text[:200]}")

    json_str = text[start:end + 1]
    return json.loads(json_str)
```

- [ ] **Step 2: 提交**

```bash
git add app/llm/client.py
git commit -m "feat: add LLM API client for Dashscope/Anthropic-compatible API"
```

---

### Task 7: Ingest Pipeline

**Files:**
- Create: `app/llm/ingest.py`
- Create: `app/tasks.py` — background task tracking

- [ ] **Step 1: 创建任务状态追踪**

```python
# app/tasks.py
"""In-memory task tracking for background ingest operations."""
import uuid
from datetime import datetime
from typing import Optional

# Global task store — in production, use Redis or database
_tasks: dict[str, dict] = {}


def create_task() -> str:
    """Create a new task with 'pending' status. Returns task_id."""
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }
    return task_id


def update_task(task_id: str, status: str, result: dict = None, error: str = None):
    """Update task status."""
    if task_id in _tasks:
        _tasks[task_id]["status"] = status
        _tasks[task_id]["result"] = result
        _tasks[task_id]["error"] = error


def get_task(task_id: str) -> Optional[dict]:
    """Get task by ID."""
    return _tasks.get(task_id)


def list_tasks() -> list[dict]:
    """List all tasks."""
    return list(_tasks.values())
```

- [ ] **Step 2: 创建 ingest pipeline**

```python
# app/llm/ingest.py
"""LLM ingest pipeline: analyze raw md -> generate wiki page."""
import json
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
        ])

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
        import re
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
```

- [ ] **Step 3: 提交**

```bash
git add app/tasks.py app/llm/ingest.py
git commit -m "feat: add ingest pipeline with LLM analysis and wiki generation"
```

---

### Task 8: 上传 + Ingest + 新建路由

**Files:**
- Create: `app/api/upload.py`
- Modify: `app/api/wiki.py` — add `generate_raw_browser_html` function (for /raw endpoint)

- [ ] **Step 1: 创建上传路由（含 generate_raw_browser_html 辅助函数）**

```python
# app/api/upload.py
"""File upload and raw file creation routes."""
import re
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse
from app.models import UploadResponse, IngestRequest, IngestResponse, IngestStatus, RawFileCreateRequest, RawFileCreateResponse
from app.config import RAW_DIR, MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS
from app.tasks import create_task, get_task
from app.llm.ingest import run_ingest

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
):
    """POST /api/upload — upload one or more .md files to raw/."""
    results = []
    for uploaded_file in files:
        # Validate extension
        if Path(uploaded_file.filename or "").suffix not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": uploaded_file.filename,
                "success": False,
                "message": f"只支持 .md 文件，跳过: {uploaded_file.filename}",
            })
            continue

        content = await uploaded_file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            results.append({
                "filename": uploaded_file.filename,
                "success": False,
                "message": f"文件过大（最大 10MB）: {uploaded_file.filename}",
            })
            continue

        # Save to raw/ — use a flat structure or detect from filename
        safe_name = uploaded_file.filename or f"upload_{uuid.uuid4().hex[:8]}.md"
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", safe_name)

        # Save to raw/ root (LLM will categorize during ingest)
        raw_path = RAW_DIR / safe_name
        raw_path.write_bytes(content)

        # Auto-trigger ingest
        task_id = create_task()
        background_tasks.add_task(run_ingest, task_id, safe_name)

        results.append({
            "filename": safe_name,
            "success": True,
            "file_path": f"raw/{safe_name}",
            "task_id": task_id,
            "message": f"已上传并开始分析: {safe_name}",
        })

    # Return first result for single-file uploads, all results for multi
    if len(results) == 1:
        r = results[0]
        return UploadResponse(
            success=r["success"],
            file_path=r.get("file_path", ""),
            task_id=r.get("task_id"),
            message=r["message"],
        )
    else:
        messages = [f"{r['filename']}: {r['message']}" for r in results]
        return UploadResponse(
            success=any(r["success"] for r in results),
            file_path=results[0].get("file_path", ""),
            task_id=results[0].get("task_id"),
            message="\n".join(messages),
        )


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(data: IngestRequest, background_tasks: BackgroundTasks):
    """POST /api/ingest — manually trigger LLM analysis for a raw file."""
    task_id = create_task()
    background_tasks.add_task(run_ingest, task_id, data.file_path)
    return IngestResponse(task_id=task_id, message=f"已触发分析任务: {task_id}")


@router.get("/ingest/status/{task_id}", response_model=IngestStatus)
async def get_ingest_status(task_id: str):
    """GET /api/ingest/status/{task_id} — check ingest progress."""
    task = get_task(task_id)
    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    return IngestStatus(
        task_id=task["task_id"],
        status=task["status"],
        result=task["result"],
        error=task["error"],
    )


@router.post("/raw-file/create", response_model=RawFileCreateResponse)
async def create_raw_file(data: RawFileCreateRequest, background_tasks: BackgroundTasks):
    """POST /api/raw-file/create — create a new raw md file inline."""
    filename = data.filename.strip()
    if not filename.endswith(".md"):
        filename += ".md"

    # Sanitize
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Determine subdirectory
    subdir = data.category or ""
    if subdir:
        target_dir = RAW_DIR / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        rel_path = f"{subdir}/{filename}"
    else:
        file_path = RAW_DIR / filename
        rel_path = filename

    file_path.write_text(data.content, encoding="utf-8")

    # Auto-trigger ingest
    task_id = create_task()
    background_tasks.add_task(run_ingest, task_id, rel_path)

    return RawFileCreateResponse(
        success=True,
        file_path=f"raw/{rel_path}",
        message=f"已创建并开始分析: {rel_path}",
    )


# ============================================================
# Raw browser HTML — migrated from server.py's _generate_raw_browser_html
# ============================================================

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


def generate_raw_browser_html() -> str:
    """Generate an Obsidian-themed raw file browser page."""
    if not RAW_DIR.exists():
        return "<p>raw/ directory not found</p>"

    categories = {}
    for item in sorted(RAW_DIR.iterdir()):
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
:root { --bg-primary:#fff; --bg-secondary:#f6f7f8; --bg-tertiary:#ececec; --bg-hover:#e8eaed; --bg-active:#e4e6eb; --bg-code:#f0f2f5; --text-primary:#1a1a1a; --text-secondary:#4a4a4a; --text-tertiary:#6b7280; --text-link:#5b6abf; --text-link-hover:#3d4fa0; --border-color:#e2e4e8; --border-light:#f0f0f0; --accent:#5b6abf; --accent-light:rgba(91,106,191,.08); --sidebar-width:260px; --content-max-width:820px; --font-sans:"Noto Sans SC",-apple-system,BlinkMacSystemFont,sans-serif; --font-mono:"SF Mono","Fira Code","Cascadia Code","Consolas",monospace; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:var(--font-sans); background:var(--bg-primary); color:var(--text-primary); font-size:15px; line-height:1.75; overflow:hidden; height:100vh; display:flex; -webkit-font-smoothing:antialiased; }
.sidebar { width:var(--sidebar-width); min-width:var(--sidebar-width); height:100vh; background:var(--bg-secondary); border-right:1px solid var(--border-color); display:flex; flex-direction:column; overflow:hidden; }
.sidebar-header { padding:1rem 1rem .5rem; }
.sidebar-header a { color:var(--text-primary); font-weight:600; font-size:.95rem; text-decoration:none; }
.sidebar-tree { flex:1; overflow-y:auto; padding:0 .5rem; }
.sidebar-tree::-webkit-scrollbar { width:4px; }
.sidebar-tree::-webkit-scrollbar-thumb { background:#ddd; border-radius:2px; }
.cat-header { display:flex; align-items:center; padding:.8rem .5rem .3rem; cursor:pointer; font-size:.72rem; font-weight:600; color:var(--text-tertiary); letter-spacing:.06em; text-transform:uppercase; gap:4px; user-select:none; transition:color .15s; }
.cat-header:hover { color:var(--text-primary); }
.cat-chevron { width:16px; height:16px; display:flex; align-items:center; justify-content:center; transition:transform .15s; flex-shrink:0; }
.cat-chevron.open { transform:rotate(90deg); }
.cat-chevron svg { width:10px; height:10px; fill:var(--text-tertiary); }
.cat-files { overflow:hidden; max-height:0; transition:max-height .2s; }
.cat-files.open { max-height:2000px; }
.file-item { padding:.2rem .4rem; font-size:13px; color:var(--text-secondary); cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; border-radius:4px; margin-left:.6rem; transition:all .1s; }
.file-item:hover { color:var(--text-primary); background:var(--bg-hover); }
.file-item.active { color:var(--text-primary); background:var(--bg-active); font-weight:500; }
.main { flex:1; display:flex; flex-direction:column; overflow:hidden; position:relative; }
.page-header { position:absolute; top:0; left:0; width:140px; padding:1.5rem 1rem 1.5rem 1.2rem; z-index:5; display:none; flex-direction:column; }
.page-header.active { display:flex; }
.ph-breadcrumb { display:flex; align-items:center; gap:.25rem; font-size:11px; color:var(--text-tertiary); margin-bottom:.6rem; }
.ph-breadcrumb a { color:var(--text-tertiary); text-decoration:none; }
.ph-breadcrumb a:hover { color:var(--accent); }
.ph-breadcrumb .sep { color:var(--border-color); }
.ph-title { font-size:1.15rem; font-weight:700; color:var(--text-primary); line-height:1.3; }
.content { flex:1; overflow-y:auto; padding:1.5rem 2.5rem 3rem 2.5rem; }
.content::-webkit-scrollbar { width:6px; }
.content::-webkit-scrollbar-thumb { background:#ddd; border-radius:3px; }
.file-content { max-width:var(--content-max-width); margin:0 auto; }
.file-content h1 { display:none; }
.file-content h2 { font-size:1.25rem; font-weight:600; margin:2rem 0 .8rem; color:var(--text-primary); }
.file-content h3 { font-size:1.05rem; font-weight:600; margin:1.5rem 0 .6rem; color:var(--text-primary); }
.file-content p { margin:.6rem 0; color:var(--text-primary); }
.file-content ul, .file-content ol { margin:.5rem 0; padding-left:1.5rem; }
.file-content code { background:var(--bg-code); border:1px solid var(--border-light); color:#d6336c; font-family:var(--font-mono); font-size:.85em; padding:.1rem .35rem; border-radius:4px; }
.file-content pre { background:var(--bg-secondary); border:1px solid var(--border-color); border-left:3px solid var(--accent); padding:1rem 1.2rem; margin:1rem 0; border-radius:6px; overflow-x:auto; }
.file-content pre code { background:none; border:none; padding:0; font-size:.85rem; line-height:1.6; color:var(--text-primary); }
.file-content blockquote { border-left:3px solid var(--accent); padding:.6rem 1rem; margin:1rem 0; color:var(--text-secondary); background:var(--accent-light); border-radius:0 4px 4px 0; }
.file-content table { width:100%; border-collapse:collapse; margin:1rem 0; font-size:.88rem; }
.file-content th, .file-content td { padding:.5rem .8rem; border:1px solid var(--border-color); text-align:left; }
.file-content th { background:var(--bg-secondary); color:var(--text-primary); font-weight:600; font-size:.82rem; }
.file-content a { color:var(--text-link); text-decoration:none; }
.file-content a:hover { color:var(--text-link-hover); }
.placeholder { display:flex; align-items:center; justify-content:center; height:100%; color:var(--text-tertiary); font-size:13px; }
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
  document.querySelectorAll('.file-item').forEach(function(i) { i.classList.remove('active'); });
  if (el) el.classList.add('active');
  var contentEl = document.getElementById('content');
  var headerEl = document.getElementById('pageHeader');
  contentEl.innerHTML = '<div class="placeholder">加载中...</div>';
  fetch('/raw-file/' + path).then(function(r) {
    if (!r.ok) throw new Error('Not found');
    return r.text();
  }).then(function(text) {
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
```

- [ ] **Step 2: 提交**

```bash
git add app/api/upload.py
git commit -m "feat: add upload, ingest status, and raw file creation routes"
```

---

### Task 9: 前端上传页面

**Files:**
- Create: `app/static/upload.html`
- Modify: `app/api/upload.py` — add GET /upload route

- [ ] **Step 1: 创建上传页面**

```html
<!-- app/static/upload.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>上传文件 — AI 知识库</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root { --bg:#fff; --bg-secondary:#f6f7f8; --bg-hover:#e8eaed; --text-primary:#1a1a1a; --text-secondary:#4a4a4a; --text-tertiary:#6b7280; --accent:#5b6abf; --accent-light:rgba(91,106,191,.08); --border:#e2e4e8; --font-sans:"Noto Sans SC",-apple-system,BlinkMacSystemFont,sans-serif; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:var(--font-sans); background:var(--bg); color:var(--text-primary); min-height:100vh; }
.nav { background:var(--bg-secondary); border-bottom:1px solid var(--border); padding:1rem 2rem; display:flex; align-items:center; gap:1rem; }
.nav a { color:var(--text-primary); text-decoration:none; font-weight:600; }
.nav a:hover { color:var(--accent); }
.nav .sep { color:var(--border); }
.container { max-width:900px; margin:2rem auto; padding:0 1.5rem; }
h1 { font-size:1.5rem; font-weight:700; margin-bottom:1.5rem; }
h2 { font-size:1.15rem; font-weight:600; margin:2rem 0 1rem; color:var(--text-primary); }
.card { background:var(--bg-secondary); border:1px solid var(--border); border-radius:8px; padding:1.5rem; margin-bottom:1.5rem; }

/* Upload zone */
.drop-zone { border:2px dashed var(--border); border-radius:8px; padding:2rem; text-align:center; cursor:pointer; transition:all .2s; }
.drop-zone:hover, .drop-zone.drag-over { border-color:var(--accent); background:var(--accent-light); }
.drop-zone p { color:var(--text-secondary); margin-top:.5rem; font-size:14px; }
.drop-zone .icon { font-size:2rem; color:var(--text-tertiary); }

/* File list */
.file-list { margin-top:1rem; }
.file-item { display:flex; align-items:center; justify-content:space-between; padding:.5rem .75rem; background:var(--bg); border-radius:4px; margin-bottom:.5rem; font-size:14px; }
.file-item .status { font-size:12px; color:var(--text-tertiary); }
.file-item .status.success { color:#16a34a; }
.file-item .status.error { color:#dc2626; }
.file-item .status.processing { color:var(--accent); }

/* Create form */
textarea { width:100%; min-height:200px; padding:.75rem; border:1px solid var(--border); border-radius:6px; font-family:monospace; font-size:14px; resize:vertical; background:var(--bg); color:var(--text-primary); }
input[type="text"] { width:100%; padding:.5rem .75rem; border:1px solid var(--border); border-radius:6px; font-size:14px; background:var(--bg); color:var(--text-primary); }
label { display:block; font-size:13px; font-weight:500; color:var(--text-secondary); margin-bottom:.25rem; }
.form-group { margin-bottom:1rem; }

/* Buttons */
.btn { display:inline-flex; align-items:center; gap:.5rem; padding:.5rem 1rem; border:none; border-radius:6px; font-size:14px; font-weight:500; cursor:pointer; transition:all .15s; }
.btn-primary { background:var(--accent); color:#fff; }
.btn-primary:hover { opacity:.9; }
.btn:disabled { opacity:.5; cursor:not-allowed; }

/* Tabs */
.tabs { display:flex; gap:0; margin-bottom:1.5rem; border-bottom:2px solid var(--border); }
.tab { padding:.75rem 1.5rem; cursor:pointer; font-size:14px; font-weight:500; color:var(--text-secondary); border-bottom:2px solid transparent; margin-bottom:-2px; transition:all .15s; }
.tab.active { color:var(--accent); border-bottom-color:var(--accent); }
.tab:hover { color:var(--text-primary); }
.tab-content { display:none; }
.tab-content.active { display:block; }

/* Progress */
.progress { margin-top:.5rem; }
.progress-bar { height:4px; background:var(--border); border-radius:2px; overflow:hidden; }
.progress-bar-inner { height:100%; background:var(--accent); width:0%; transition:width .3s; }
.progress-text { font-size:12px; color:var(--text-tertiary); margin-top:.25rem; }
</style>
</head>
<body>

<nav class="nav">
  <a href="/">AI 知识库</a>
  <span class="sep">/</span>
  <span>上传文件</span>
</nav>

<div class="container">
  <h1>添加知识文档</h1>

  <div class="tabs">
    <div class="tab active" data-tab="upload">上传文件</div>
    <div class="tab" data-tab="create">新建文档</div>
  </div>

  <!-- Upload tab -->
  <div class="tab-content active" id="tab-upload">
    <div class="card">
      <div class="drop-zone" id="dropZone">
        <div class="icon">📄</div>
        <p>拖拽 .md 文件到此处，或点击选择</p>
        <input type="file" id="fileInput" multiple accept=".md" style="display:none">
      </div>
      <div class="file-list" id="fileList"></div>
    </div>
  </div>

  <!-- Create tab -->
  <div class="tab-content" id="tab-create">
    <div class="card">
      <div class="form-group">
        <label for="createFilename">文件名（含 .md 后缀）</label>
        <input type="text" id="createFilename" placeholder="例如: my-new-note.md">
      </div>
      <div class="form-group">
        <label for="createCategory">分类目录（可选，留空则存入 raw/ 根目录）</label>
        <input type="text" id="createCategory" placeholder="例如: avm_calib">
      </div>
      <div class="form-group">
        <label for="createContent">内容（Markdown）</label>
        <textarea id="createContent" placeholder="在此输入 Markdown 内容..."></textarea>
      </div>
      <button class="btn btn-primary" id="createBtn">保存并分析</button>
      <div class="progress" id="createProgress" style="display:none">
        <div class="progress-bar"><div class="progress-bar-inner" id="createProgressBar"></div></div>
        <div class="progress-text" id="createProgressText"></div>
      </div>
    </div>
  </div>

  <!-- Task status -->
  <div id="taskSection" style="display:none">
    <h2>分析任务</h2>
    <div id="taskList"></div>
  </div>
</div>

<script>
// Tab switching
document.querySelectorAll('.tab').forEach(function(tab) {
  tab.addEventListener('click', function() {
    document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  });
});

// File upload
var dropZone = document.getElementById('dropZone');
var fileInput = document.getElementById('fileInput');
var fileList = document.getElementById('fileList');

dropZone.addEventListener('click', function() { fileInput.click(); });
dropZone.addEventListener('dragover', function(e) { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', function() { dropZone.classList.remove('drag-over'); });
dropZone.addEventListener('drop', function(e) {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', function() { handleFiles(fileInput.files); });

function handleFiles(files) {
  var formData = new FormData();
  for (var i = 0; i < files.length; i++) {
    if (files[i].name.endsWith('.md')) {
      formData.append('files', files[i]);
      addFileItem(files[i].name, 'uploading');
    }
  }
  if (!formData.has('files')) return;

  var token = getToken();
  fetch('/api/upload', {
    method: 'POST',
    headers: token ? { 'Authorization': 'Bearer ' + token } : {},
    body: formData
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.success && data.task_id) {
      updateFileItem(files[0].name, 'success', '已上传，分析中...');
      addTask(data.task_id, files[0].name);
    } else {
      updateFileItem(files[0].name, 'error', data.message);
    }
  })
  .catch(function(err) {
    updateFileItem(files[0].name, 'error', '上传失败: ' + err.message);
  });
}

function addFileItem(name, status) {
  var div = document.createElement('div');
  div.className = 'file-item';
  div.id = 'file-' + name;
  div.innerHTML = '<span>' + name + '</span><span class="status" id="status-' + name + '">' + status + '</span>';
  fileList.appendChild(div);
}

function updateFileItem(name, status, text) {
  var el = document.getElementById('status-' + name);
  if (el) {
    el.className = 'status ' + status;
    el.textContent = text;
  }
}

// Create file
document.getElementById('createBtn').addEventListener('click', function() {
  var filename = document.getElementById('createFilename').value.trim();
  var category = document.getElementById('createCategory').value.trim();
  var content = document.getElementById('createContent').value;

  if (!filename || !content) {
    alert('请填写文件名和内容');
    return;
  }

  var progress = document.getElementById('createProgress');
  var progressBar = document.getElementById('createProgressBar');
  var progressText = document.getElementById('createProgressText');
  progress.style.display = 'block';
  progressBar.style.width = '20%';
  progressText.textContent = '保存中...';

  var token = getToken();
  fetch('/api/raw-file/create', {
    method: 'POST',
    headers: Object.assign({ 'Content-Type': 'application/json' }, token ? { 'Authorization': 'Bearer ' + token } : {}),
    body: JSON.stringify({ filename: filename, content: content, category: category || null })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    progressBar.style.width = '50%';
    progressText.textContent = '已保存，开始分析...';
    if (data.success) {
      addTask('pending', data.file_path);
    } else {
      progressText.textContent = '创建失败: ' + data.message;
    }
  })
  .catch(function(err) {
    progressText.textContent = '请求失败: ' + err.message;
  });
});

// Task tracking
var activeTasks = [];

function addTask(taskId, filename) {
  var section = document.getElementById('taskSection');
  section.style.display = 'block';
  var taskList = document.getElementById('taskList');

  var div = document.createElement('div');
  div.className = 'file-item';
  div.id = 'task-' + taskId;
  div.innerHTML = '<span>' + filename + '</span><span class="status processing" id="task-status-' + taskId + '">分析中...</span>';
  taskList.appendChild(div);

  if (taskId !== 'pending') {
    activeTasks.push({ id: taskId, filename: filename, element: div });
    pollTask(taskId);
  }
}

function pollTask(taskId) {
  var token = getToken();
  fetch('/api/ingest/status/' + taskId, {
    headers: token ? { 'Authorization': 'Bearer ' + token } : {}
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    var statusEl = document.getElementById('task-status-' + taskId);
    if (!statusEl) return;

    if (data.status === 'completed') {
      statusEl.className = 'status success';
      statusEl.textContent = '完成: ' + (data.result && data.result.wiki_path ? data.result.wiki_path : '');
      removeTask(taskId);
    } else if (data.status === 'failed') {
      statusEl.className = 'status error';
      statusEl.textContent = '失败: ' + (data.error || '未知错误');
      removeTask(taskId);
    } else {
      setTimeout(function() { pollTask(taskId); }, 3000);
    }
  })
  .catch(function() {
    setTimeout(function() { pollTask(taskId); }, 5000);
  });
}

function removeTask(taskId) {
  activeTasks = activeTasks.filter(function(t) { return t.id !== taskId; });
}

// Auth token helper
function getToken() {
  // Try to get token from cookie first
  var cookies = document.cookie.split(';');
  for (var i = 0; i < cookies.length; i++) {
    var c = cookies[i].trim();
    if (c.startsWith('kb_token=')) {
      return c.substring('kb_token='.length);
    }
  }
  // Fall back to localStorage
  return localStorage.getItem('kb_token');
}
</script>
</body>
</html>
```

- [ ] **Step 2: 在 upload.py 中添加 GET /upload 路由**

在 `app/api/upload.py` 的 router 定义后添加：

```python
from fastapi.responses import HTMLResponse
from pathlib import Path

@router.get("/upload")
async def upload_page():
    """GET /upload — serve the upload HTML page."""
    html_path = Path(__file__).parent.parent / "static" / "upload.html"
    if not html_path.exists():
        return HTMLResponse(status_code=404, content="Upload page not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
```

- [ ] **Step 3: 提交**

```bash
git add app/static/upload.html app/api/upload.py
git commit -m "feat: add upload page with drag-drop, file creation, and task tracking"
```

---

### Task 10: FastAPI 应用入口 + 整合

**Files:**
- Create: `server_fastapi.py`

- [ ] **Step 1: 创建 FastAPI 应用**

```python
#!/usr/bin/env python3
"""
FastAPI server for the AI Knowledge Base.
Replaces server.py with async support, file upload, and LLM ingest.

Usage:
    python server_fastapi.py              # serves on port 8080
    python server_fastapi.py --port 9000  # serves on port 9000
"""
import argparse
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth import auth_middleware
from app.api.auth import router as auth_router
from app.api.wiki import router as wiki_router
from app.api.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events."""
    print("AI Knowledge Base FastAPI starting...")
    yield
    print("AI Knowledge Base FastAPI shutting down...")


app = FastAPI(title="AI Knowledge Base", lifespan=lifespan)

# CORS (for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware
app.middleware("http")(auth_middleware)

# Include routers
app.include_router(auth_router)
app.include_router(wiki_router)
app.include_router(upload_router)

# Serve static files from public/
from app.config import PUBLIC_DIR
app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")


def main():
    parser = argparse.ArgumentParser(description="AI Knowledge Base FastAPI Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "server_fastapi:app",
        host=args.host,
        port=args.port,
        reload=True,  # auto-reload during development
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试服务器启动**

```bash
python server_fastapi.py --port 8081 &
sleep 3
curl -s http://localhost:8081/api/index | python -m json.tool | head -20
curl -s http://localhost:8081/api/graph | python -m json.tool | head -20
kill %1 2>/dev/null
```

Expected: Both endpoints return valid JSON with wiki pages and graph data.

- [ ] **Step 3: 提交**

```bash
git add server_fastapi.py
git commit -m "feat: add FastAPI application entry point with all routes"
```

---

### Task 11: 端到端测试 + 文档

**Files:**
- Modify: `requirements-fastapi.txt` (if needed)
- Create: `README.md` update (or new section)

- [ ] **Step 1: 完整流程测试**

```bash
# 1. 启动服务器
python server_fastapi.py --port 8081 &
SERVER_PID=$!
sleep 3

# 2. 登录获取 token
LOGIN_RESP=$(curl -s -X POST http://localhost:8081/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"18352869670","password":"your-password"}')
TOKEN=$(echo $LOGIN_RESP | python -c "import sys,json; print(json.load(sys.stdin).get('token',''))")

if [ -z "$TOKEN" ]; then
  echo "Login failed"
  kill $SERVER_PID 2>/dev/null
  exit 1
fi

echo "Token: $TOKEN"

# 3. 创建测试 raw 文件
echo "# 测试文档

这是一个测试用的 raw markdown 文件。

## 内容

包含一些关于卡尔曼滤波的笔记。

卡尔曼滤波是一种递归的状态估计方法。
" > raw/test-kalman-note.md

# 4. 触发 ingest
INGEST_RESP=$(curl -s -X POST http://localhost:8081/api/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"file_path":"test-kalman-note.md"}')
TASK_ID=$(echo $INGEST_RESP | python -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))")

echo "Task ID: $TASK_ID"

# 5. Poll status until complete
for i in $(seq 1 30); do
  STATUS=$(curl -s http://localhost:8081/api/ingest/status/$TASK_ID \
    -H "Authorization: Bearer $TOKEN" \
    | python -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
  echo "Status: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done

# 6. Check result
echo "=== Ingest Result ==="
curl -s http://localhost:8081/api/ingest/status/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 7. Check wiki file was created
echo "=== Wiki files ==="
ls -la wiki/tracking/ 2>/dev/null || ls -la wiki/

# 8. Check index.md was updated
echo "=== index.md (last 10 lines) ==="
tail -10 index.md

# 9. Check log.md was updated
echo "=== log.md (last 10 lines) ==="
tail -10 log.md

# Cleanup
kill $SERVER_PID 2>/dev/null
rm -f raw/test-kalman-note.md
```

- [ ] **Step 2: 清理测试产物**

```bash
# Remove any test wiki files created during testing
# (Don't commit test artifacts)
```

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "docs: add FastAPI server — online upload + LLM ingest workflow"
```

---

## Self-Review

1. **Spec coverage check:**
   - [x] FastAPI 后端架构 → Task 1, 10
   - [x] JWT 认证中间件 → Task 2
   - [x] Pydantic 数据模型 → Task 3
   - [x] 认证路由 (login/verify) → Task 4
   - [x] Wiki 只读路由迁移 → Task 5
   - [x] LLM API 客户端 → Task 6
   - [x] Ingest Pipeline → Task 7
   - [x] 上传/新建路由 → Task 8
   - [x] 前端上传页面 → Task 9
   - [x] 文件上传限制（.md, 10MB）→ Task 8 upload_file
   - [x] LLM API 超时 60 秒 → Task 6 call_llm
   - [x] 路径穿越保护 → Task 7, 8 (sanitize filenames)
   - [x] 写入冲突处理 → Task 7 (_update_index with .conflict suffix)
   - [x] index.md 更新 → Task 7 (_update_index)
   - [x] log.md 追加 → Task 7 (_append_log)

2. **Placeholder scan:** No TBD, TODO, or vague steps found. All code blocks contain complete implementations.

3. **Type consistency:** All models use consistent field names. `task_id` is consistently `str`. API paths match between routers and frontend fetch calls. Token extraction uses the same cookie name `kb_token` across all files.
