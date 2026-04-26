---
title: 在线添加 raw 文件 + LLM 自动 ingest 功能设计
author: Claude
date: 2026-04-26
status: draft
---

# 在线添加 Raw 文件 + LLM 自动 Ingest — 设计文档

## 1. 问题陈述

当前知识库的 `server.py` 是一个只读的 Python stdlib HTTP 服务器，仅支持 GET 请求。raw 文件需要手动放入 `raw/` 目录，然后手动调用 LLM 触发 ingest 流程。

**目标：** 提供 Web 界面，支持在线上传/新建 raw md 文件，上传后自动调用 LLM 分析并生成正式的 wiki 页面（完整 ingest 流程）。

## 2. 架构决策

### 2.1 后端框架：FastAPI

| 选项 | 取舍 | 未选原因 |
|------|------|----------|
| **FastAPI** | async 原生、文件上传好、JWT 中间件成熟 | — |
| Flask | 轻量、同步、生态成熟 | LLM API 调用是 I/O 密集型，同步模型不天然适配 |
| 扩展 server.py | 零依赖、改动最小 | POST + multipart + 外部 API 调用超出 stdlib 舒适区 |

### 2.2 认证：复用现有 JWT 机制

现有 `server.py` 已有 JWT 认证 + cookie 回退机制。FastAPI 端通过相同 secret key 签发/验证 token，实现统一认证。

### 2.3 LLM API：Dashscope qwen3.6-plus

使用 `~/.claude/settings.json` 中配置的 API：
- Base URL: `https://coding.dashscope.aliyuncs.com/apps/anthropic`
- Auth Token: `sk-sp-c390987f0f1a49f8843e9fc96b09c6f7`
- Model: `qwen3.6-plus`

## 3. 模块设计

### 3.1 目录结构

```
ai-knowledge-base/
├── server.py                  # 保留，作为备用/对比
├── server_fastapi.py          # 新的 FastAPI 应用入口
├── app/
│   ├── __init__.py
│   ├── auth.py                # JWT 认证中间件（复用现有逻辑）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── upload.py          # POST /api/upload — 文件上传
│   │   ├── ingest.py          # POST /api/ingest — 触发 LLM 分析
│   │   ├── status.py          # GET /api/ingest/status/{task_id} — 查询进度
│   │   └── wiki.py            # 从 server.py 迁移的 wiki 只读 API
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py          # LLM API 客户端
│   │   └── ingest.py          # Ingest pipeline 逻辑
│   ├── models.py              # 数据模型（Pydantic）
│   └── static/
│       └── upload.html        # 上传/新建页面
├── raw/                       # 不变
└── wiki/                      # 不变
```

### 3.2 API 端点

| 方法 | 路径 | 认证 | 描述 |
|------|------|------|------|
| GET | `/` | 否 | Docsify 首页（保留） |
| GET | `/api/index` | 否 | wiki 索引 |
| GET | `/api/graph` | 否 | 关系图谱 |
| GET | `/upload` | 否 | 上传页面（未登录用户看到登录提示） |
| POST | `/api/upload` | 是 | 上传 md 文件（multipart） |
| POST | `/api/ingest` | 是 | 触发 LLM 分析指定文件 |
| GET | `/api/ingest/status/{task_id}` | 是 | 查询 ingest 进度 |
| POST | `/api/raw-file/create` | 是 | 在线新建 raw md 文件 |

### 3.3 JWT 认证中间件

```python
# app/auth.py
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "fallback")  # 与 server.py 一致

async def verify_auth(request: Request, call_next):
    # 白名单：不需要认证的路径
    if request.url.path in ("/", "/api/index", "/api/graph", "/upload", "/favicon.ico"):
        return await call_next(request)

    # 尝试从 cookie 或 Authorization header 获取 token
    token = request.cookies.get("jwt_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return RedirectResponse(url="/login")

    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return RedirectResponse(url="/login")

    return await call_next(request)
```

### 3.4 LLM Ingest Pipeline

**Prompt 设计：**

```
你是一个知识库 ingest 引擎。请分析以下 raw markdown 文件，并生成符合规范的 wiki 页面。

要求：
1. 提取关键概念、公式、算法、架构图
2. 判断所属分类（从以下选择一个：3dgs, avm, calibration, perception, tracking, fusion, platform, tools）
3. 搜索现有 wiki 内容，决定创建新页面还是更新已有页面
4. 生成 wiki 页面内容，包含：
   - YAML frontmatter（title, category, tags, created, updated, sources）
   - 结构化的正文内容
   - ## 相关页面 章节，链接到相关 wiki 页面

当前 wiki 索引如下：
{index_content}

Raw 文件内容：
{raw_content}

请以 JSON 格式返回：
{
  "category": "分类",
  "filename": "kebab-case-文件名.md",
  "action": "create" | "update",
  "target_path": "wiki/分类/文件名",
  "wiki_content": "完整的 wiki 页面内容（markdown）"
}
```

**流程：**

```
POST /api/ingest → BackgroundTasks.start_ingest(task_id, file_path)
    │
    ├── 读取 raw 文件内容
    ├── 读取 index.md 获取当前索引
    ├── 调用 LLM API（qwen3.6-plus）
    │    └── 解析返回的 JSON
    ├── 写入 wiki/<category>/<filename>.md
    ├── 更新 index.md
    ├── 追加 log.md
    └── 更新任务状态为 "completed"
```

**错误处理：**
- LLM API 超时/失败：任务标记为 "failed"，文件保留在 raw/
- JSON 解析失败：记录原始响应到 log.md，任务失败
- 写入冲突（目标文件已存在）：追加 `.conflict` 后缀，不覆盖

### 3.5 前端上传页面

`/upload` 页面包含：

1. **登录状态检测**：未登录显示登录按钮，已登录显示上传区域
2. **文件上传区**：拖拽 + 点击上传，支持多文件
3. **新建文件区**：textarea 编辑器 + 文件名输入
4. **任务状态区**：显示当前 ingest 任务进度（轮询 `/api/ingest/status/`）
5. **成功反馈**：显示生成的 wiki 页面链接

### 3.6 数据模型

```python
# app/models.py
from pydantic import BaseModel
from typing import Optional

class UploadResponse(BaseModel):
    success: bool
    file_path: str
    task_id: Optional[str] = None  # 如果自动触发 ingest
    message: str

class IngestRequest(BaseModel):
    file_path: str  # raw/ 下的相对路径

class IngestResponse(BaseModel):
    task_id: str
    message: str

class IngestStatus(BaseModel):
    task_id: str
    status: str  # "pending" | "processing" | "completed" | "failed"
    result: Optional[dict] = None  # 成功时的结果信息
    error: Optional[str] = None  # 失败时的错误信息
```

## 4. 安全考虑

- JWT secret key 从环境变量读取，不硬编码
- 上传文件限制：`.md` 后缀、最大 10MB
- LLM API 调用超时：30 秒
- 写入操作只在 `wiki/` 和 `raw/` 目录内，不允许路径穿越

## 5. 迁移策略

1. 创建 `server_fastapi.py` 和 `app/` 模块
2. 将 `server.py` 中的只读 API 迁移到 FastAPI（`/api/index`、`/api/graph` 等）
3. 添加新的上传/ingest 端点
4. 前端页面放到 `app/static/upload.html`
5. 测试：上传、LLM 分析、wiki 生成、索引更新
6. 文档：更新 README，记录新的启动方式

## 6. 验收标准

1. 访问 `/upload` 可以看到上传页面（未登录需先登录）
2. 上传 md 文件后，自动触发 LLM 分析
3. 分析完成后，wiki/ 下生成对应的 wiki 页面
4. index.md 和 log.md 已更新
5. 生成的 wiki 页面符合规范（frontmatter 完整、交叉引用正确）
6. 失败场景有明确的错误提示
