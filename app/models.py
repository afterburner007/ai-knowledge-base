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
