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
