# Login System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JWT-based authentication protecting all wiki content, requiring login before access.

**Architecture:** JWT tokens stored in localStorage, validated server-side via Authorization header. All routes except `/login` and `/api/auth/login` are protected. Single hardcoded user with salted SHA-256 password hash.

**Tech Stack:** PyJWT, hashlib, secrets, Python stdlib HTTP server, plain HTML/CSS/JS frontend

---

### File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `public/login.html` | Login page — YouthSprint-inspired split layout |
| Modify | `server.py:1-21` | Add new imports: jwt, hashlib, secrets, json, time, urllib |
| Modify | `server.py:22-36` | Add JWT_SECRET, TOKEN_EXPIRY, password hash utility, USERS dict |
| Modify | `server.py:37-75` | Add generate_token(), verify_token(), hash_password() functions |
| Modify | `server.py:127-162` | Modify do_GET: add auth check before routing, add /login route |
| Modify | `server.py:522-524` | Add do_POST() method for /api/auth/login |
| Modify | `server.py:527-544` | Add serve_login_page(), handle_login(), handle_verify() handlers |
| Modify | `server.py:main()` | Print login URL on startup |

---

### Task 1: Install PyJWT + Add Auth Infrastructure to server.py

**Files:**
- Modify: `server.py` (lines 12-21 for imports, lines 22-36 for auth constants)

- [ ] **Step 1: Install PyJWT dependency**

Run: `pip install PyJWT`

Expected: `Successfully installed PyJWT-X.X.X`

- [ ] **Step 2: Add new imports after line 17**

Insert after `import argparse` (line 17):

```python
import jwt
import hashlib
import secrets
import time
from urllib.parse import unquote
```

Note: `from urllib.parse import unquote` replaces the existing import at line 20. Remove `from urllib.parse import unquote` from line 20 since we're moving it up. The final import block should be:

```python
import os
import sys
import re
import json
import argparse
import jwt
import hashlib
import secrets
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote
```

- [ ] **Step 3: Add auth constants and utilities after line 36 (after CATEGORY_NAMES)**

Add after `CATEGORY_NAMES` closing brace:

```python
# JWT authentication
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
    return pwd_hash == parts[2]


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


# User database: {phone_number: {"password_hash": "...", "username": "..."}}
# Password for 18352869670 is "yuange666"
USERS = {
    "18352869670": {
        "password_hash": hash_password("yuange666"),
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add server.py
git commit -m "feat: add JWT auth infrastructure + single user"
```

---

### Task 2: Create Login Page (public/login.html)

**Files:**
- Create: `public/login.html`

- [ ] **Step 1: Create login page with split layout**

Create `public/login.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>登录 — AI 知识库</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --font-sans: "Noto Sans SC", -apple-system, BlinkMacSystemFont, sans-serif;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--font-sans); overflow: hidden; height: 100vh; }

.login-container { display: flex; width: 100vw; height: 100vh; }

/* Left brand panel */
.brand-section {
  flex: 0 0 60%;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.brand-section::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(circle at 20% 80%, rgba(91,106,191,0.2) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(139,92,246,0.15) 0%, transparent 50%);
  pointer-events: none;
}
.brand-content { position: relative; z-index: 1; padding: 4rem; color: white; }
.logo-icon {
  width: 80px; height: 80px; margin: 0 auto 1.5rem;
  background: linear-gradient(135deg, #5b6abf 0%, #8b5cf6 100%);
  border-radius: 18px; display: flex; align-items: center; justify-content: center;
  font-size: 2rem; font-weight: 700;
  box-shadow: 0 10px 40px rgba(91,106,191,0.4);
}
.brand-title {
  font-size: 2.25rem; font-weight: 700; text-align: center; margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #a5b4fc 0%, #c4b5fd 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.brand-subtitle { text-align: center; font-size: 1rem; color: #94a3b8; margin-bottom: 3rem; }
.feature-item {
  display: flex; align-items: flex-start; gap: 1rem; padding: 1.25rem 1.5rem;
  background: rgba(255,255,255,0.05); border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.1); margin-bottom: 1.25rem;
  transition: all 0.3s ease;
}
.feature-item:hover { background: rgba(255,255,255,0.08); transform: translateX(6px); }
.feature-icon { font-size: 1.5rem; flex-shrink: 0; }
.feature-text h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem; }
.feature-text p { font-size: 0.85rem; color: #94a3b8; }

/* Right form panel */
.form-section {
  flex: 0 0 40%; background: #f8fafc;
  display: flex; align-items: center; justify-content: center;
}
.form-wrapper { width: 100%; max-width: 400px; padding: 3rem; }
.form-header { margin-bottom: 2rem; }
.form-title { font-size: 1.75rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; }
.form-subtitle { font-size: 0.95rem; color: #64748b; }

.input-group { margin-bottom: 1.25rem; }
.input-group label { display: block; font-size: 0.85rem; font-weight: 500; color: #475569; margin-bottom: 0.4rem; }
.input-group input {
  width: 100%; padding: 0.85rem 1rem; border: 1px solid #e2e8f0;
  border-radius: 8px; font-size: 0.95rem; font-family: var(--font-sans);
  transition: all 0.2s ease; outline: none; background: white;
}
.input-group input:focus { border-color: #5b6abf; box-shadow: 0 0 0 3px rgba(91,106,191,0.1); }
.input-group input.error { border-color: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.1); }

.login-btn {
  width: 100%; padding: 0.85rem; border: none; border-radius: 8px;
  background: linear-gradient(135deg, #5b6abf 0%, #3d4fa0 100%);
  color: white; font-size: 1rem; font-weight: 600; font-family: var(--font-sans);
  cursor: pointer; transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(91,106,191,0.3);
}
.login-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(91,106,191,0.4); }
.login-btn:disabled { opacity: 0.7; cursor: not-allowed; }

.error-msg {
  display: none; padding: 0.75rem 1rem; background: #fef2f2;
  border: 1px solid #fecaca; border-radius: 8px;
  color: #dc2626; font-size: 0.875rem; margin-bottom: 1.25rem;
}
.error-msg.visible { display: block; }

@media (max-width: 768px) {
  .login-container { flex-direction: column; }
  .brand-section { flex: none; min-height: 35vh; }
  .brand-content { padding: 2rem 1.5rem; }
  .feature-item { display: none; }
  .form-section { flex: 1; }
  .form-wrapper { padding: 2rem 1.5rem; }
}
</style>
</head>
<body>
<div class="login-container">
  <!-- Left brand panel -->
  <div class="brand-section">
    <div class="brand-content">
      <div class="logo-icon">KB</div>
      <h1 class="brand-title">AI 知识库</h1>
      <p class="brand-subtitle">自动驾驶标定与感知知识管理系统</p>
      <div class="features-list">
        <div class="feature-item">
          <span class="feature-icon">📚</span>
          <div class="feature-text"><h3>结构化知识</h3><p>wiki 页面关联，交叉引用网络</p></div>
        </div>
        <div class="feature-item">
          <span class="feature-icon">🔍</span>
          <div class="feature-text"><h3>关系图谱</h3><p>可视化知识关联，图谱探索</p></div>
        </div>
        <div class="feature-item">
          <span class="feature-icon">📊</span>
          <div class="feature-text"><h3>原始文件浏览</h3><p>Obsidian 主题，源文件直接查看</p></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Right form panel -->
  <div class="form-section">
    <div class="form-wrapper">
      <div class="form-header">
        <h2 class="form-title">登录</h2>
        <p class="form-subtitle">请输入您的账号信息</p>
      </div>

      <div class="error-msg" id="errorMsg">账号或密码错误</div>

      <form id="loginForm" onsubmit="return handleLogin(event)">
        <div class="input-group">
          <label for="username">手机号</label>
          <input type="text" id="username" name="username" placeholder="请输入手机号" autocomplete="username" required>
        </div>
        <div class="input-group">
          <label for="password">密码</label>
          <input type="password" id="password" name="password" placeholder="请输入密码" autocomplete="current-password" required>
        </div>
        <button type="submit" class="login-btn" id="loginBtn">登录</button>
      </form>
    </div>
  </div>
</div>

<script>
function handleLogin(e) {
  e.preventDefault();
  var btn = document.getElementById('loginBtn');
  var errorEl = document.getElementById('errorMsg');
  var username = document.getElementById('username').value.trim();
  var password = document.getElementById('password').value;

  errorEl.classList.remove('visible');
  btn.disabled = true;
  btn.textContent = '登录中...';

  fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: username, password: password })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.success) {
      localStorage.setItem('kb_token', data.token);
      window.location.href = '/';
    } else {
      errorEl.textContent = data.message || '账号或密码错误';
      errorEl.classList.add('visible');
      btn.disabled = false;
      btn.textContent = '登录';
    }
  })
  .catch(function() {
    errorEl.textContent = '登录请求失败，请检查网络';
    errorEl.classList.add('visible');
    btn.disabled = false;
    btn.textContent = '登录';
  });

  return false;
}

// If already logged in, redirect to home
(function() {
  var token = localStorage.getItem('kb_token');
  if (token) {
    fetch('/api/auth/verify', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.valid) { window.location.href = '/'; }
    })
    .catch(function() {});
  }
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add public/login.html
git commit -m "feat: add login page — split layout with brand + form"
```

---

### Task 3: Add Auth Endpoints (POST /api/auth/login + GET /api/auth/verify)

**Files:**
- Modify: `server.py` (add do_POST method, add serve_login_page/handle_login/handle_verify handlers)

- [ ] **Step 1: Add do_POST method before the `log_message` method (~line 523)**

Add before `def log_message(self, format, *args):`:

```python
    def do_POST(self):
        """Handle POST requests — auth endpoints."""
        path = self.path.split("?")[0]
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
        return self._send_json({
            "success": True,
            "message": "登录成功",
            "token": token,
        })

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
        """Extract Bearer token from Authorization header."""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _require_auth(self):
        """Check authentication. Returns True if valid, sends redirect/401 if not."""
        token = self._get_auth_token()
        if not token:
            self._redirect_to_login()
            return False
        payload = verify_token(token)
        if not payload:
            self._redirect_to_login()
            return False
        return True

    def _redirect_to_login(self):
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
```

- [ ] **Step 2: Add /api/auth/verify to do_GET**

In the existing `do_GET` method, add a new elif branch for `/api/auth/verify` alongside the other API routes. Find this block (around line 149-156):

```python
        elif path == "/api/index":
            self.serve_api_index()
        elif path == "/api/wiki-path-map":
            self.serve_path_map()
        elif path == "/api/graph":
            self.serve_graph()
```

Add `/api/auth/verify` before the other API routes (it needs auth, but the others also need it — we'll add auth checks in Task 4):

```python
        elif path == "/api/auth/verify":
            self.handle_verify()
        elif path == "/api/index":
```

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat: add auth endpoints — login, verify, and helper methods"
```

---

### Task 4: Protect All Routes with Auth Middleware

**Files:**
- Modify: `server.py` (do_GET method, lines 131-162)

- [ ] **Step 1: Add auth check at the start of do_GET routing**

Modify the `do_GET` method. The current routing block (lines 139-161) looks like:

```python
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
```

Replace it with auth-protected routing. Only `/login` and `/api/auth/login` are unprotected. Add auth check right after the `/login` handling:

```python
        # Unprotected routes
        if path == "/login":
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
```

Important: The `/login` check must come BEFORE the `_require_auth()` call. The `/api/auth/verify` route must appear after the auth check since it IS the auth check endpoint (but it's also protected by `_require_auth()` — that's intentional, it validates the token passed in the header).

Wait — `/api/auth/verify` needs to be reachable to check if a token is valid. If `_require_auth()` fails, it sends a 401. So calling `/api/auth/verify` without a token would get a 401 from `_require_auth()` before reaching `handle_verify()`. This is actually fine — both paths return 401 for unauthenticated requests. But the login page's auto-redirect logic calls `/api/auth/verify` with a token, and if the token is valid, `_require_auth()` passes and `handle_verify()` returns `{"valid": True}`.

- [ ] **Step 2: Update frontend JS to attach token to all requests**

The login page already stores the token in localStorage after login. The wiki is served by Docsify (public/index.html) which fetches markdown via GET requests. We need Docsify's requests to include the Authorization header.

Add to `public/index.html` (or the main Docsify page) a script that intercepts fetch requests. But since we don't know the current index.html structure, the simpler approach: the auth check redirects unauthenticated requests to `/login`. After login, the user is redirected to `/`. On `/`, the browser makes GET requests to `_sidebar.md`, wiki pages, etc. These are regular browser GET requests — they won't have `Authorization: Bearer` headers.

**Critical design decision:** Since wiki pages are loaded by the browser directly (not via JS fetch), we can't attach Bearer tokens. Instead, after successful login, set a **cookie** alongside the localStorage token. The cookie will be sent automatically with browser GET requests.

Modify `handle_login()` in server.py — add Set-Cookie header. Replace the current `_send_json` call in `handle_login`:

```python
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
```

Modify `_get_auth_token()` to also check cookies:

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat: protect all routes with JWT auth middleware + cookie fallback"
```

---

### Task 5: Add Login URL to Startup Message + End-to-End Test

**Files:**
- Modify: `server.py` (main() function, print statement)

- [ ] **Step 1: Add login URL to startup message**

In the `main()` function, find:

```python
    print(f"AI Knowledge Base running at http://localhost:{args.port}")
    print(f"Accessible on LAN at http://<your-ip>:{args.port}")
```

Replace with:

```python
    print(f"AI Knowledge Base running at http://localhost:{args.port}")
    print(f"Login at http://localhost:{args.port}/login")
    print(f"Accessible on LAN at http://<your-ip>:{args.port}")
```

- [ ] **Step 2: Install PyJWT if not already done**

Run: `pip install PyJWT`

- [ ] **Step 3: Start server and test login flow**

Start the server: `python server.py --port 8080`

Expected output:
```
AI Knowledge Base running at http://localhost:8080
Login at http://localhost:8080/login
Accessible on LAN at http://<your-ip>:8080
```

- [ ] **Step 4: Test login with curl**

Test unauthenticated access (should redirect):
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
```
Expected: `302`

Test login with wrong credentials:
```bash
curl -s -X POST http://localhost:8080/api/auth/login -H "Content-Type: application/json" -d '{"username":"wrong","password":"wrong"}'
```
Expected: `{"success": false, "message": "账号或密码错误"}`

Test login with correct credentials:
```bash
curl -s -X POST http://localhost:8080/api/auth/login -H "Content-Type: application/json" -d '{"username":"18352869670","password":"yuange666"}'
```
Expected: `{"success": true, "message": "登录成功", "token": "eyJ..."}`

Test authenticated access (replace TOKEN with the token from above):
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ -H "Authorization: Bearer TOKEN"
```
Expected: `200`

- [ ] **Step 5: Stop server and commit**

```bash
git add server.py
git commit -m "chore: add login URL to startup message"
```
