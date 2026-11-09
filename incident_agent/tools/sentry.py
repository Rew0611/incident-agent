"""Read-only Sentry tools: list organization issues and inspect one issue's latest event."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from claude_agent_sdk import tool

from ..config import get, require
from ._common import ok, request, safe

NAME = "sentry"
REQUIRED_ENV = ("SENTRY_AUTH_TOKEN", "SENTRY_ORG")
CONTEXT = """\
Sentry holds application errors (issues) and the events behind them.
Use sentry_list_issues to find recent or matching issues; `query` takes Sentry search syntax, e.g. "is:unresolved level:error".
Use sentry_get_issue with an issue id, short id (e.g. PROJ-1A) or Sentry issue URL to see its latest stack trace, breadcrumbs and tags.
"""

TAG_KEYS = ("release", "environment", "transaction", "url")
CRUMB_KEYS = ("timestamp", "category", "level", "message", "data")


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


def _frame(frame: dict) -> dict:
    """Location and source line of one stack frame."""
    lineno = frame.get("lineNo")
    line = next((text for no, text in frame.get("context") or [] if no == lineno), None)
    return {
        "filename": frame.get("filename"),
        "function": frame.get("function"),
        "lineno": lineno,
        "context_line": line.strip() if line else None,
    }


def _condense(event: dict) -> dict:
    """Keep only what helps debugging: exceptions, recent breadcrumbs, key tags."""
    entries = {e.get("type"): e.get("data") or {} for e in event.get("entries") or []}
    exceptions = []
    for exc in (entries.get("exception") or {}).get("values") or []:
        frames = (exc.get("stacktrace") or {}).get("frames") or []
        in_app = [f for f in frames if f.get("inApp")]
        shown = in_app[-20:] or frames[-5:]  # frames run oldest -> crash site
        exceptions.append({"type": exc.get("type"), "value": exc.get("value"), "frames": [_frame(f) for f in shown]})
    crumbs = (entries.get("breadcrumbs") or {}).get("values") or []
    return {
        "eventID": event.get("eventID"),
        "dateCreated": event.get("dateCreated"),
        "message": event.get("message"),
        "exceptions": exceptions,
        "breadcrumbs": [{k: b[k] for k in CRUMB_KEYS if b.get(k)} for b in crumbs[-10:]],
        "tags": {t["key"]: t.get("value") for t in event.get("tags") or [] if t.get("key") in TAG_KEYS},
    }


async def _issue_id(raw: str) -> str:
    """Numeric issue id from an id, short id, or issue URL."""
    ref = raw.strip()
    if match := re.search(r"/issues/([^/?#]+)", ref):
        ref = match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", ref):
        raise ValueError(f"Not a Sentry issue id, short id or issue URL: {raw!r}")
    if ref.isdigit():
        return ref
    return str((await _get(f"shortids/{ref}/"))["groupId"])


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


@tool(
    "sentry_get_issue",
    "Get one Sentry issue plus its latest event: exception, in-app stack frames, recent breadcrumbs, key tags.",
    {
        "type": "object",
        "properties": {
            "issue": {"type": "string", "description": "Numeric issue id, short id (e.g. PROJ-1A), or Sentry issue URL."},
        },
        "required": ["issue"],
    },
)
@safe
async def sentry_get_issue(args: dict) -> dict:
    """Issue summary and a condensed view of its latest event."""
    gid = await _issue_id(str(args["issue"]))
    issue, event = await asyncio.gather(_get(f"issues/{gid}/"), _get(f"issues/{gid}/events/latest/"))
    return ok({**_summary(issue), "status": issue.get("status"), "latest_event": _condense(event)})


TOOLS = [sentry_list_issues, sentry_get_issue]
