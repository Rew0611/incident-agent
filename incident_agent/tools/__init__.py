"""Tool packs. A pack is a module that defines NAME, REQUIRED_ENV, CONTEXT and TOOLS.

A pack is mounted only when all of its REQUIRED_ENV values are set, so an
integration is enabled just by filling in its section of .env.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server

from .. import config
from . import elasticsearch, github, pagerduty, sentry

PACKS: tuple[ModuleType, ...] = (pagerduty, sentry, elasticsearch, github)


def enabled() -> list[ModuleType]:
    return [p for p in PACKS if all(config.get(name) for name in p.REQUIRED_ENV)]


def mount(packs: list[ModuleType]) -> tuple[dict[str, Any], list[str], str]:
    """Return MCP servers, fully qualified tool names, and usage notes for the packs."""
    servers = {p.NAME: create_sdk_mcp_server(name=p.NAME, tools=p.TOOLS) for p in packs}
    names = [f"mcp__{p.NAME}__{t.name}" for p in packs for t in p.TOOLS]
    notes = "\n\n".join(f"## {p.NAME}\n{p.CONTEXT.strip()}" for p in packs)
    return servers, names, notes
