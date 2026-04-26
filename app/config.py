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
