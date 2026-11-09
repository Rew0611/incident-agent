"""Command line: incident-agent "<task>" [--repo PATH|owner/name] [--base BRANCH] [--fix]"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from claude_agent_sdk import ClaudeSDKError

from . import agent, config, workspace


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="incident-agent",
        description="Investigate incidents with PagerDuty, Sentry and Elasticsearch, then fix the code.",
    )
    parser.add_argument("task", help='e.g. "Why is PagerDuty incident Q1ABC2D firing?"')
    parser.add_argument("--repo", default=".", help="local path, or GitHub repo as owner/name or URL (default: .)")
    parser.add_argument("--base", help="GitHub branch to start from (default: the repo's default branch)")
    parser.add_argument("--fix", action="store_true", help="let the agent edit files; for GitHub repos, open a PR")
    args = parser.parse_args()

    path = Path(args.repo).expanduser()
    github_repo = None if path.is_dir() else workspace.parse_repo(args.repo)
    if not path.is_dir() and not github_repo:
        parser.error(f"--repo: {args.repo} is neither a directory nor a GitHub repo (owner/name)")

    config.load_env()
    try:
        task = args.task
        if github_repo:
            path, base = workspace.checkout(github_repo, args.base)
            task += f"\n\nRepository: {github_repo} (branch {base}), checked out in the working directory."
        summary = asyncio.run(agent.run(task, path.resolve(), fix=args.fix))
        if github_repo and args.fix:
            title = f"incident-agent: {args.task[:60]}"
            url = workspace.open_pr(path, github_repo, base, title, summary or args.task)
            print(f"\nPull request: {url}" if url else "\nNo file changes, so no pull request.")
    except (ClaudeSDKError, RuntimeError, httpx.HTTPError, ValueError) as e:
        sys.exit(f"error: {e}")
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
