"""Read-only Elasticsearch log tools over the REST API (_search and _mapping only)."""

from __future__ import annotations

import re
from typing import Any

from claude_agent_sdk import tool

from ..config import get, require
from ._common import ok, request, safe

NAME = "elasticsearch"
REQUIRED_ENV = ("ELASTICSEARCH_URL",)
CONTEXT = """Elasticsearch holds application logs. es_search_logs reads the actual lines.
Queries use Lucene syntax, e.g. `level:error AND service.name:api`. Default window: last 60 minutes."""

_INDEX = {"type": "string", "description": "Index pattern. Default: ELASTICSEARCH_INDEX or logs-*."}
_QUERY = {"type": "string", "description": "Lucene query_string syntax. Default '*' (all)."}
_MINUTES = {"type": "integer", "description": "Look back this many minutes from now. Default 60."}


def _url(args: dict, endpoint: str) -> str:
    """<base>/<index>/<endpoint>; the index is allowlisted so it cannot change the path."""
    index = args.get("index") or get("ELASTICSEARCH_INDEX", "logs-*")
    if not re.fullmatch(r"[\w.*,:+-]+", index):
        raise ValueError(f"Invalid index pattern: {index!r}")
    return f"{require('ELASTICSEARCH_URL').rstrip('/')}/{index}/{endpoint}"


def _auth() -> dict[str, Any]:
    """httpx kwargs for API-key or basic auth, if configured."""
    if key := get("ELASTICSEARCH_API_KEY"):
        return {"headers": {"Authorization": f"ApiKey {key}"}}
    user, password = get("ELASTICSEARCH_USERNAME"), get("ELASTICSEARCH_PASSWORD")
    return {"auth": (user, password)} if user and password else {}


async def _search(args: dict, **body: Any) -> dict:
    """POST _search filtered by time range (start/end or minutes_back) and the optional query."""
    if args.get("start") or args.get("end"):
        rng = {"format": "strict_date_optional_time", "gte": args.get("start"), "lte": args.get("end")}
        rng = {k: v for k, v in rng.items() if v}
    else:
        rng = {"gte": f"now-{int(args.get('minutes_back', 60))}m"}
    filters: list[dict] = [{"range": {get("ELASTICSEARCH_TIMESTAMP_FIELD", "@timestamp"): rng}}]
    if (query := (args.get("query") or "*").strip()) != "*":
        filters.append({"query_string": {"query": query}})
    body = {"query": {"bool": {"filter": filters}}, "track_total_hits": True, **body}
    return await request("POST", _url(args, "_search"), json=body, **_auth())


def _pluck(doc: Any, path: str) -> Any:
    """Dotted field from _source, whether stored nested or as a literal dotted key."""
    if not isinstance(doc, dict):
        return None
    if path in doc:
        return doc[path]
    head, _, rest = path.partition(".")
    return _pluck(doc.get(head), rest) if rest else None


@tool(
    "es_search_logs",
    "Search logs newest first. Returns total hits and one line per hit: timestamp | message | extra fields.",
    {
        "type": "object",
        "properties": {
            "query": _QUERY,
            "minutes_back": _MINUTES,
            "start": {"type": "string", "description": "ISO time, e.g. 2026-01-31T14:00:00Z. Overrides minutes_back."},
            "end": {"type": "string", "description": "ISO time; use with start."},
            "size": {"type": "integer", "description": "Hits to return. Default 50, max 200."},
            "fields": {"type": "array", "items": {"type": "string"}, "description": "Extra fields to show."},
            "index": _INDEX,
        },
        "required": [],
    },
)
@safe
async def es_search_logs(args: dict) -> dict:
    ts = get("ELASTICSEARCH_TIMESTAMP_FIELD", "@timestamp")
    msg = get("ELASTICSEARCH_MESSAGE_FIELD", "message")
    extra = list(args.get("fields") or [])
    resp = await _search(
        args,
        sort=[{ts: {"order": "desc", "unmapped_type": "date"}}],
        size=max(1, min(int(args.get("size", 50)), 200)),
        _source=[ts, msg, *extra],
    )
    hits = resp["hits"]["hits"]
    lines = [f"{resp['hits']['total']['value']} total hits, showing {len(hits)} newest:"]
    for hit in hits:
        src = hit.get("_source", {})
        text = " ".join(str(_pluck(src, msg) or "").split())
        line = f"{_pluck(src, ts)} | {text[:300]}{'...' if len(text) > 300 else ''}"
        lines.append(" | ".join([line, *(f"{f}={_pluck(src, f)}" for f in extra)]))
    return ok("\n".join(lines))


TOOLS = [es_search_logs]
