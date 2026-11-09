"""Shared pieces for tool packs: HTTP calls and the tool-result shape."""

from __future__ import annotations

import functools
import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

MAX_CHARS = 20_000  # keep each tool result small enough for the model's context

Result = dict[str, Any]


def ok(data: Any) -> Result:
    """Successful tool result. Dicts/lists are rendered as JSON."""
    text = data if isinstance(data, str) else json.dumps(data, indent=2, default=str)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + f"\n... [truncated {len(text) - MAX_CHARS} chars]"
    return {"content": [{"type": "text", "text": text}]}


def fail(message: str) -> Result:
    """Error result: the model sees the message instead of the run crashing."""
    return {"content": [{"type": "text", "text": message}], "is_error": True}


async def request(method: str, url: str, **kwargs: Any) -> Any:
    """Send an HTTP request and return the parsed JSON body."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()


def safe(fn: Callable[[dict[str, Any]], Awaitable[Result]]) -> Callable[[dict[str, Any]], Awaitable[Result]]:
    """Turn HTTP, config and input errors inside a tool into a `fail` result."""

    @functools.wraps(fn)
    async def wrapper(args: dict[str, Any]) -> Result:
        try:
            return await fn(args)
        except httpx.HTTPStatusError as e:
            return fail(f"HTTP {e.response.status_code} from {e.request.url}: {e.response.text[:500]}")
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as e:
            return fail(f"{type(e).__name__}: {e}")

    return wrapper
