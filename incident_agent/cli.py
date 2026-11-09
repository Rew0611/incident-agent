"""Command line: incident-agent "<task>" [--repo PATH] [--fix]"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeSDKError

from . import agent, config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="incident-agent",
        description="Investigate incidents with PagerDuty, Sentry and Elasticsearch, then fix the code.",
    )
    parser.add_argument("task", help='e.g. "Why is PagerDuty incident Q1ABC2D firing?"')
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository to work in (default: current dir)")
    parser.add_argument("--fix", action="store_true", help="let the agent edit files (default: read-only)")
    args = parser.parse_args()

    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        parser.error(f"--repo: {repo} is not a directory")

    config.load_env()
    try:
        asyncio.run(agent.run(args.task, repo, fix=args.fix))
    except ClaudeSDKError as e:
        sys.exit(f"error: {e}")
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
