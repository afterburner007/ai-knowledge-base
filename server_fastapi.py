#!/usr/bin/env python3
"""
FastAPI server for the AI Knowledge Base.
Replaces server.py with async support, file upload, and LLM ingest.

Usage:
    python3 server_fastapi.py              # serves on port 8080
    python3 server_fastapi.py --port 9000  # serves on port 9000
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
