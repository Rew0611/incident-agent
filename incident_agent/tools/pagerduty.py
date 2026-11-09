"""Read-only PagerDuty tools (REST API v2): recent incidents."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from claude_agent_sdk import tool

from .. import config
from ._common import ok, request, safe

NAME = "pagerduty"
REQUIRED_ENV = ("PAGERDUTY_API_TOKEN",)
CONTEXT = """PagerDuty (read-only): use pd_list_incidents to see what paged recently and when."""

STATUSES = ["triggered", "acknowledged", "resolved"]


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET a REST API v2 path with token auth and the v2 Accept header."""
    base = config.get("PAGERDUTY_BASE_URL", "https://api.pagerduty.com").rstrip("/")
    headers = {
        "Authorization": f"Token token={config.require('PAGERDUTY_API_TOKEN')}",
        "Accept": "application/vnd.pagerduty+json;version=2",
    }
    return await request("GET", base + path, headers=headers, params=params)


def _name(ref: dict[str, Any] | None) -> str | None:
    """Display name of a PagerDuty reference object (service, user, priority)."""
    return (ref or {}).get("summary")


@tool(
    "pd_list_incidents",
    "List recent PagerDuty incidents, newest first: id, number, title, status, urgency, service, "
    "created_at and link.",
    {
        "type": "object",
        "properties": {
            "statuses": {"type": "array", "items": {"type": "string", "enum": STATUSES},
                         "description": "Only these statuses. Default: all."},
            "since_hours": {"type": "number", "description": "Look back this many hours. Default 24."},
            "limit": {"type": "integer", "description": "Max incidents. Default 20, max 100."},
            "service_ids": {"type": "array", "items": {"type": "string"},
                            "description": "Only these PagerDuty service IDs."},
        },
        "required": [],
    },
)
@safe
async def pd_list_incidents(args: dict[str, Any]) -> dict[str, Any]:
    """Recent incidents in a compact form."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=float(args.get("since_hours") or 24))
    params: dict[str, Any] = {
        "since": since.isoformat(timespec="seconds"),
        "until": now.isoformat(timespec="seconds"),
        "limit": max(1, min(int(args.get("limit") or 20), 100)),
        "sort_by": "created_at:desc",
    }
    if args.get("statuses"):
        params["statuses[]"] = list(args["statuses"])
    if args.get("service_ids"):
        params["service_ids[]"] = list(args["service_ids"])

    data = await _get("/incidents", params)
    incidents = [
        {"id": i["id"], "number": i.get("incident_number"), "title": i.get("title"),
         "status": i.get("status"), "urgency": i.get("urgency"), "service": _name(i.get("service")),
         "created_at": i.get("created_at"), "html_url": i.get("html_url")}
        for i in data.get("incidents", [])
    ]
    return ok({"incidents": incidents, "more": data.get("more", False)})


TOOLS = [pd_list_incidents]
