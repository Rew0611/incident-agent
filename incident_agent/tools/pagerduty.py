"""Read-only PagerDuty tools (REST API v2): recent incidents and incident details."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from claude_agent_sdk import tool

from .. import config
from ._common import ok, request, safe

NAME = "pagerduty"
REQUIRED_ENV = ("PAGERDUTY_API_TOKEN",)
CONTEXT = """PagerDuty (read-only): use pd_list_incidents to see what paged recently and when,
then pd_get_incident for one incident's alerts, timeline and notes.
Alert `details` usually hold the monitoring payload (host, check, query, error text):
use them as leads for log, metric and error searches."""

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


def _latest(items: list[dict[str, Any]], n: int = 10) -> list[dict[str, Any]]:
    return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)[:n]


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


@tool(
    "pd_get_incident",
    "Get one PagerDuty incident: core fields, assignees, latest notes and timeline entries, and its "
    "newest alerts with their `details` (the monitoring payload).",
    {
        "type": "object",
        "properties": {"id": {"type": "string", "description": "Incident ID (e.g. PT4KHLK) or number."}},
        "required": ["id"],
    },
)
@safe
async def pd_get_incident(args: dict[str, Any]) -> dict[str, Any]:
    """Incident details plus alerts, overview log entries and notes."""
    inc = (await _get(f"/incidents/{quote(str(args['id']), safe='')}"))["incident"]
    path = f"/incidents/{inc['id']}"
    alerts, log, notes = await asyncio.gather(
        _get(f"{path}/alerts", {"limit": 10, "sort_by": "created_at:desc"}),
        _get(f"{path}/log_entries", {"is_overview": "true", "limit": 100}),
        _get(f"{path}/notes"),
    )
    return ok({
        "id": inc["id"],
        "number": inc.get("incident_number"),
        "title": inc.get("title"),
        "status": inc.get("status"),
        "urgency": inc.get("urgency"),
        "priority": _name(inc.get("priority")),
        "service": _name(inc.get("service")),
        "created_at": inc.get("created_at"),
        "last_status_change_at": inc.get("last_status_change_at"),
        "assignees": [_name(a.get("assignee")) for a in inc.get("assignments", [])],
        "alert_counts": inc.get("alert_counts"),
        "html_url": inc.get("html_url"),
        "notes": [
            {"at": n.get("created_at"), "by": _name(n.get("user")), "content": n.get("content")}
            for n in _latest(notes.get("notes", []))
        ],
        "log_entries": [
            {"at": e.get("created_at"), "type": e.get("type"), "summary": e.get("summary")}
            for e in _latest(log.get("log_entries", []))
        ],
        # Kept last so the result size cap trims large alert payloads before anything else.
        "alerts": [
            {"id": a.get("id"), "summary": a.get("summary"), "status": a.get("status"),
             "severity": a.get("severity"), "created_at": a.get("created_at"),
             "details": (a.get("body") or {}).get("details")}
            for a in alerts.get("alerts", [])
        ],
    })


TOOLS = [pd_list_incidents, pd_get_incident]
