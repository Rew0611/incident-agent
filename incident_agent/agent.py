"""The agent: which tools each mode gets, and how a run is shown in the terminal."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from . import config, prompts, tools

DEFAULT_MODEL = "claude-opus-5-5"
READ_TOOLS = ["Read", "Grep", "Glob"]
WRITE_TOOLS = ["Edit", "Write"]


def build_options(repo: Path, fix: bool) -> ClaudeAgentOptions:
    """Tool grants are the safety boundary: investigate mode has no write tools at all."""
    packs = tools.enabled()
    if not packs:
        raise SystemExit("No integrations configured. Fill in .env (see sample.env).")
    servers, tool_names, notes = tools.mount(packs)
    builtins = READ_TOOLS + (WRITE_TOOLS if fix else [])
    mode = prompts.FIX if fix else prompts.INVESTIGATE
    return ClaudeAgentOptions(
        model=config.get("AGENT_MODEL", DEFAULT_MODEL),
        cwd=repo,
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": f"{prompts.BASE}\n\n{mode}\n\n# Integrations\n{notes}",
        },
        tools=builtins,  # the only built-in tools the model can see (no shell)
        allowed_tools=builtins + tool_names,  # pre-approved
        permission_mode="dontAsk",  # anything not pre-approved is denied, never prompted
        mcp_servers=servers,
        setting_sources=[],  # ignore local Claude settings so runs are predictable
        max_turns=int(config.get("AGENT_MAX_TURNS", "40")),
        env={"ENABLE_TOOL_SEARCH": "false"},  # few tools: load all definitions upfront
    )


async def run(task: str, repo: Path, fix: bool = False) -> None:
    """Run one task, printing the agent's messages and tool calls as they happen."""
    async for message in query(prompt=task, options=build_options(repo, fix)):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, flush=True)
                elif isinstance(block, ToolUseBlock):
                    print(f"  > {block.name} {_brief(block.input)}", flush=True)
        elif isinstance(message, ResultMessage):
            cost = f"${message.total_cost_usd:.2f}" if message.total_cost_usd is not None else "n/a"
            print(f"\n[{message.subtype}] turns={message.num_turns} cost={cost}")


def _brief(args: dict[str, Any], limit: int = 120) -> str:
    text = ", ".join(f"{k}={v!r}" for k, v in args.items())
    return text if len(text) <= limit else text[: limit - 3] + "..."
