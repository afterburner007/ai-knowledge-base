# Subdomain Deployment Design — wiki.wudibyd.cloud

**Date:** 2026-05-05
**Type:** deployment
**Status:** approved

## Problem

The domain `wudibyd.cloud` is already in use by the YouthSprint project. We need to deploy the AI Knowledge Base on the same domain without affecting YouthSprint's functionality.

## Decision

Use a subdomain (`wiki.wudibyd.cloud`) for the knowledge base, with a separate nginx server block and PM2-managed process.

## Architecture

```
                         wudibyd.cloud
                        /             \
              wiki.wudibyd.cloud        wudibyd.cloud (root)
              ┌──────────────┐         ┌─────────────────────┐
              │ nginx :443   │         │ nginx :443          │
              │ server_name: │         │ server_name:        │
              │ wiki.wudibyd │         │ wudibyd.cloud       │
              └──────┬───────┘         └──────┬──────────────┘
                     │                        │
              proxy_pass              static files + /api/
              ↓                         ↓
         KB server                 YouthSprint
         :8080 (FastAPI)           :3000 (Node.js)
```

## Implementation Details

### 1. DNS

Add an A record in the domain registrar console:
- **Host:** `wiki`
- **Value:** Server IP (same as `wudibyd.cloud`)
- **TTL:** 600 (10 min) or default

### 2. SSL Certificate

The existing certificate at `/home/ubuntu/code/wudibyd.pem` is a wildcard certificate covering:
- `DNS:*.wudibyd.cloud`
- `DNS:wudibyd.cloud`

No new certificate needed. `wiki.wudibyd.cloud` is already covered.

### 3. Nginx Configuration

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

Enable with: `ln -s /etc/nginx/sites-available/ai-knowledge-base /etc/nginx/sites-enabled/ai-knowledge-base`

### 4. PM2 Process

Add a new app entry to the existing `ecosystem.config.cjs` in the ai-knowledge-base project (not YouthSprint's):

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

Start with: `cd /home/ubuntu/code/ai-knowledge-base && pm2 start ecosystem.config.cjs`

### 5. Log Directory

Create `/var/log/ai-kb/` with proper permissions: `sudo mkdir -p /var/log/ai-kb && sudo chmod 755 /var/log/ai-kb`

## Isolation Guarantees

| Concern | How it's handled |
|---------|------------------|
| YouthSprint nginx config | Unchanged — separate server_name directive |
| Port conflict | KB on 8080, YouthSprint on 3000 |
| SSL certificate | Wildcard cert already covers `*.wudibyd.cloud` |
| File system | Each project has its own directories |
| Process management | Separate PM2 ecosystem config |
| DNS | Separate A record, same IP |

## Verification Steps

1. `nginx -t` passes after adding new config
2. `wiki.wudibyd.cloud` resolves to server IP (`dig wiki.wudibyd.cloud`)
3. `curl -I https://wiki.wudibyd.cloud` returns 200
4. YouthSprint still works at `https://wudibyd.cloud`
5. PM2 shows both apps running: `pm2 list`
