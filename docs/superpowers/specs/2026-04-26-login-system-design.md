# Login System Design — AI Knowledge Base

> Inspired by YouthSprint's JWT authentication architecture.

## Summary

Add JWT-based authentication to the knowledge base server, protecting all routes except `/login`. A standalone HTML login page provides the frontend interface. Single hardcoded user for now.

## Architecture

### Flow
1. User visits any page → server checks for valid JWT in `Authorization: Bearer` header
2. If missing/invalid → redirect to `/login`
3. `/login` serves a standalone HTML login page
4. User submits credentials to `POST /api/auth/login`
5. Server validates against hardcoded users dict, returns JWT
6. Frontend stores token in `localStorage`
7. All subsequent requests include `Authorization: Bearer <token>`

### Protected Routes
All routes except `/login` require authentication:
- `/` (home), `/README.md`, `/_sidebar.md`
- `/wiki/*`, `/raw`, `/raw-file/*`
- `/api/*` (index, wiki-path-map, graph)
- `/graph`, `/graph.html`

### Unprotected Routes
- `/login` — login page
- `/api/auth/login` — login endpoint
- Static assets: `/docsify-theme.css`, `favicon`

## Backend (`server.py`)

### Users Storage
Hardcoded dict mapping phone numbers to user records:
```python
USERS = {
    "18352869670": {
        "password_hash": "sha256:salt:hash",
        "username": "yuange666"
    }
}
```
Password hash generated once at startup or via utility function. Uses `hashlib.sha256` with random salt (no bcrypt dependency).

### JWT Configuration
- Secret key: generated at startup via `secrets.token_hex(32)`
- Token expiry: 24 hours
- Payload: `{"sub": username, "exp": unix_timestamp}`

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/login` | Serve login HTML page |
| POST | `/api/auth/login` | Accept `{"username", "password"}`, return `{"success": true, "token": "JWT"}` |
| GET | `/api/auth/verify` | Validate current token, return `{"valid": true, "user": "..."}` |

### Auth Middleware
Wrapper function applied to all existing `do_GET` branches:
1. Extract `Authorization: Bearer <token>` from request headers
2. Call `verify_token()` to decode and validate
3. If invalid → redirect to `/login` (HTTP 302) or return 401 for `/api/*` routes
4. If valid → proceed with original handler

## Frontend (`public/login.html`)

### Layout
YouthSprint-inspired split design:
- **Left panel (60%):** Dark gradient background, "AI 知识库" branding, key feature highlights
- **Right panel (40%):** Light background, centered login form

### Form
- Username input (phone/email)
- Password input with show/hide toggle
- "登录" button with loading state
- Error message display on failure

### Behavior
- On submit: POST to `/api/auth/login`
- On success: `localStorage.setItem('kb_token', token)`, redirect to `/`
- On failure: show "账号或密码错误"
- Redirects `/` already has token → passes auth middleware → no login page loop

## Dependencies

- `PyJWT` — JWT encoding/decoding (`pip install PyJWT`)
- `hashlib`, `secrets` — stdlib for hashing and secret generation

## Security Notes

- JWT secret generated at runtime (not hardcoded)
- Passwords stored as salted SHA-256 hashes
- No plaintext passwords in source
- For production: use environment variable for JWT secret, switch to bcrypt

## Exclusions (YAGNI)

- No registration, no password reset (no DB)
- No multi-user roles
- No "remember me" / persistent sessions beyond token expiry
- No rate limiting on login attempts
