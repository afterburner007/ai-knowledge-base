# app/llm/client.py
"""LLM API client — communicates with Dashscope/Anthropic-compatible API."""
import httpx
import json
import re
from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL


async def call_llm(messages: list[dict], temperature: float = 0.3, timeout: float = 60.0) -> str:
    """Call LLM API and return response text."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/v1/messages",
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": 8192,
                "temperature": temperature,
                "messages": messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # Anthropic-style response
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block["text"]
        raise ValueError(f"Unexpected LLM response format: {data}")


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response (may contain markdown code blocks)."""
    # Try to find JSON in code blocks
    m = re.search(r"```(?:json)?\n([\s\S]*?)\n```", text)
    if m:
        text = m.group(1)

    # Find JSON object — may be nested
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in response: {text[:200]}")

    json_str = text[start:end + 1]
    return json.loads(json_str)
