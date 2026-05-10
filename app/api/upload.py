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
        task_id=task_id,
        message=f"已创建并开始分析: {rel_path}",
    )


@router.get("/upload")
async def upload_page():
    """GET /upload — serve the upload HTML page."""
    html_path = Path(__file__).parent.parent / "static" / "upload.html"
    if not html_path.exists():
        return HTMLResponse(status_code=404, content="Upload page not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


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
