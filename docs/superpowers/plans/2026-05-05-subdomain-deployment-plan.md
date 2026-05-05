# Subdomain Deployment — wiki.wudibyd.cloud

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy AI Knowledge Base on `wiki.wudibyd.cloud` subdomain without affecting YouthSprint at `wudibyd.cloud`.

**Architecture:** Separate nginx server block for `wiki.wudibyd.cloud` reverse-proxying to FastAPI on port 8080, managed by PM2. Wildcard SSL certificate (`*.wudibyd.cloud`) reused.

**Tech Stack:** nginx, PM2, uvicorn (FastAPI), Python 3

---

### Task 1: Create nginx configuration for wiki.wudibyd.cloud

**Files:**
- Create: `/etc/nginx/sites-available/ai-knowledge-base`
- Symlink: `/etc/nginx/sites-enabled/ai-knowledge-base`

- [ ] **Step 1: Write nginx site config**

Create `/etc/nginx/sites-available/ai-knowledge-base`:

```nginx
server {
    listen 443 ssl;
    server_name wiki.wudibyd.cloud;

    ssl_certificate /home/ubuntu/code/wudibyd.pem;
    ssl_certificate_key /home/ubuntu/code/wudibyd.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;

    # Reverse proxy to FastAPI server
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Hidden file protection
    location ~ /\. {
        deny all;
    }

    client_max_body_size 50M;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name wiki.wudibyd.cloud;
    return 301 https://$server_name$request_uri;
}
```

- [ ] **Step 2: Enable the site**

```bash
sudo ln -s /etc/nginx/sites-available/ai-knowledge-base /etc/nginx/sites-enabled/ai-knowledge-base
```

- [ ] **Step 3: Test nginx configuration**

```bash
sudo nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

- [ ] **Step 4: Reload nginx**

```bash
sudo systemctl reload nginx
```

- [ ] **Step 5: Verify YouthSprint is unaffected**

```bash
curl -sI https://wudibyd.cloud | head -5
```

Expected: HTTP/2 200 or HTTP/1.1 200 (not 502, not 404)

### Task 2: Create log directory

**Files:**
- Create directory: `/var/log/ai-kb/`

- [ ] **Step 1: Create log directory**

```bash
sudo mkdir -p /var/log/ai-kb && sudo chown ubuntu:ubuntu /var/log/ai-kb
```

- [ ] **Step 2: Verify directory exists and is writable**

```bash
ls -la /var/log/ | grep ai-kb
```

Expected output shows `ai-kb` directory owned by `ubuntu`.

### Task 3: Create PM2 ecosystem config

**Files:**
- Create: `ecosystem.config.cjs` (project root)

- [ ] **Step 1: Write ecosystem config**

Create `/home/ubuntu/code/ai-knowledge-base/ecosystem.config.cjs`:

```javascript
module.exports = {
  apps: [{
    name: 'ai-kb',
    script: 'server_fastapi.py',
    interpreter: 'python3',
    cwd: '/home/ubuntu/code/ai-knowledge-base',
    instances: 1,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      PORT: 8080,
    },
    error_file: '/var/log/ai-kb/error.log',
    out_file: '/var/log/ai-kb/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M'
  }]
};
```

Note: `reload=True` in `server_fastapi.py:67` is a dev-only setting. PM2 manages the process lifecycle, so the auto-reload won't cause issues in production (PM2 will restart the process on crash regardless).

- [ ] **Step 2: Commit ecosystem config**

```bash
git add ecosystem.config.cjs
git commit -m "feat: add PM2 ecosystem config for production deployment"
```

### Task 4: Start PM2 process

- [ ] **Step 1: Start the knowledge base with PM2**

```bash
cd /home/ubuntu/code/ai-knowledge-base && pm2 start ecosystem.config.cjs
```

- [ ] **Step 2: Verify PM2 shows both apps**

```bash
pm2 list
```

Expected output shows both `youthsprint-api` and `ai-kb` with status `online`:

```
┌────┬────────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name               │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼────────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│  0 │ ai-kb              │ default     │ N/A     │ fork    │ <pid>    │ <time> │ 0    │ online    │ 0%       │ <mem>    │ ubuntu   │ disabled │
│  1 │ youthsprint-api    │ default     │ 1.0.0   │ fork    │ <pid>    │ <time> │ 3    │ online    │ 0%       │ <mem>    │ ubuntu   │ disabled │
└────┴────────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
```

- [ ] **Step 3: Save PM2 process list for auto-start on reboot**

```bash
pm2 save
```

- [ ] **Step 4: Test local endpoint**

```bash
curl -sI http://127.0.0.1:8080 | head -5
```

Expected: Should return a redirect (302 to /login) or 200 response.

### Task 5: DNS configuration (manual step)

This step requires manual action in the domain registrar's DNS console.

- [ ] **Step 1: Add DNS A record**

Add the following DNS record in your domain registrar's DNS management console:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | wiki | 13.114.6.98 | 600 |

- [ ] **Step 2: Verify DNS propagation**

```bash
dig wiki.wudibyd.cloud +short
```

Expected: `13.114.6.98`

Note: DNS propagation may take a few minutes. If the result is empty, wait and retry.

### Task 6: End-to-end verification

- [ ] **Step 1: Test HTTPS access to wiki.wudibyd.cloud**

```bash
curl -sI https://wiki.wudibyd.cloud
```

Expected: `HTTP/2 302` (redirect to /login — auth is required)

- [ ] **Step 2: Test that login page loads**

```bash
curl -s https://wiki.wudibyd.cloud/login | head -20
```

Expected: HTML content of the login page.

- [ ] **Step 3: Verify YouthSprint still works**

```bash
curl -sI https://wudibyd.cloud | head -5
```

Expected: `HTTP/2 200` (or redirect to HTTPS).

- [ ] **Step 4: Verify both PM2 processes are online**

```bash
pm2 list
```

Expected: Both `ai-kb` and `youthsprint-api` showing `online`.

- [ ] **Step 5: Check nginx error logs for issues**

```bash
sudo tail -20 /var/log/nginx/error.log
```

Expected: No errors related to `wiki.wudibyd.cloud` or port 8080.
