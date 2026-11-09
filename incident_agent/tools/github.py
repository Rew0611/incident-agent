"""Read-only GitHub tool: recent commits, to line up incidents with code changes."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from claude_agent_sdk import tool

from ..config import require
from ._common import ok, request, safe

NAME = "github"
REQUIRED_ENV = ("GITHUB_TOKEN",)
CONTEXT = """GitHub (read-only): use gh_recent_commits to see what changed shortly before an incident
started; compare commit times with when the incident fired and when errors were first seen."""


@tool(
    "gh_recent_commits",
    "Recent commits on a GitHub repo branch, newest first: sha, time, author, message, link.",
    {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "owner/name"},
            "since_hours": {"type": "number", "description": "Look back this many hours. Default 72."},
            "branch": {"type": "string", "description": "Branch or sha. Default: the repo's default branch."},
            "path": {"type": "string", "description": "Only commits touching this file or directory."},
            "limit": {"type": "integer", "description": "Max commits. Default 30, max 100."},
        },
        "required": ["repo"],
    },
)
@safe
async def gh_recent_commits(args: dict[str, Any]) -> dict[str, Any]:
    repo = args["repo"]
    if not re.fullmatch(r"[\w-]+/[\w.-]+", repo):
        raise ValueError(f"repo must be owner/name, got {repo!r}")
    since = datetime.now(timezone.utc) - timedelta(hours=float(args.get("since_hours") or 72))
    params = {"since": since.isoformat(timespec="seconds"), "per_page": max(1, min(int(args.get("limit") or 30), 100))}
    if args.get("path"):
        params["path"] = args["path"]
    if args.get("branch"):
        params["sha"] = args["branch"]
    headers = {
        "Authorization": f"Bearer {require('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    commits = await request("GET", f"https://api.github.com/repos/{repo}/commits", headers=headers, params=params)
    return ok([
        {
            "sha": c["sha"][:10],
            "date": c["commit"]["author"]["date"],
            "author": (c.get("author") or {}).get("login") or c["commit"]["author"]["name"],
            "message": c["commit"]["message"].splitlines()[0],
            "url": c["html_url"],
        }
        for c in commits
    ])


TOOLS = [gh_recent_commits]
