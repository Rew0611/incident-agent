"""Read-only Sentry tools: list organization issues."""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import tool

from ..config import get, require
from ._common import ok, request, safe

NAME = "sentry"
REQUIRED_ENV = ("SENTRY_AUTH_TOKEN", "SENTRY_ORG")
CONTEXT = """\
Sentry holds application errors (issues) and the events behind them.
Use sentry_list_issues to find recent or matching issues; `query` takes Sentry search syntax, e.g. "is:unresolved level:error".
"""


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET an organization-scoped Sentry API path."""
    base = get("SENTRY_BASE_URL", "https://sentry.io").rstrip("/")
    url = f"{base}/api/0/organizations/{require('SENTRY_ORG')}/{path}"
    headers = {"Authorization": f"Bearer {require('SENTRY_AUTH_TOKEN')}"}
    return await request("GET", url, params=params, headers=headers)


def _summary(issue: dict) -> dict:
    """Compact view of an issue."""
    keys = ("id", "shortId", "title", "culprit", "level", "count", "userCount", "firstSeen", "lastSeen")
    return {
        **{k: issue.get(k) for k in keys},
        "project": (issue.get("project") or {}).get("slug"),
        "permalink": issue.get("permalink"),
    }


@tool(
    "sentry_list_issues",
    "List Sentry issues in the organization with event/user counts, first/last seen and links.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": 'Sentry search syntax. Default "is:unresolved"; "" for all.'},
            "stats_period": {"type": "string", "description": 'Time window such as "1h", "24h", "7d". Default "24h".'},
            "limit": {"type": "integer", "description": "Max issues to return (1-100). Default 20."},
        },
        "required": [],
    },
)
@safe
async def sentry_list_issues(args: dict) -> dict:
    """List organization issues matching a search query."""
    params = {
        "query": args.get("query", "is:unresolved"),
        "statsPeriod": args.get("stats_period") or "24h",
        "limit": max(1, min(int(args.get("limit") or 20), 100)),
    }
    return ok([_summary(issue) for issue in await _get("issues/", params)])


TOOLS = [sentry_list_issues]
