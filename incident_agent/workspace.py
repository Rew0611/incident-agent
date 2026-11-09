"""GitHub workspace: clone a repo into a local cache.

Git runs here, in code, never by the model; the agent only reads and edits files in
the clone. The token is passed to git through the environment, never via argv or disk.
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx

from . import config

API = "https://api.github.com"
REPO_RE = re.compile(r"(?:https://github\.com/)?([\w-]+/[\w.-]+?)(?:\.git)?/?")


def parse_repo(value: str) -> str | None:
    """'owner/name' from 'owner/name' or a github.com URL, else None."""
    match = REPO_RE.fullmatch(value.strip())
    return match.group(1) if match else None


def _api(method: str, path: str, **kwargs: Any) -> Any:
    headers = {
        "Authorization": f"Bearer {config.require('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = httpx.request(method, API + path, headers=headers, timeout=30, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _git(cwd: Path, *args: str, check: bool = True) -> str:
    basic = base64.b64encode(f"x-access-token:{config.require('GITHUB_TOKEN')}".encode()).decode()
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic}",
    }
    proc = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
    if check and proc.returncode:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def checkout(repo: str, base: str | None = None) -> tuple[Path, str]:
    """Clone or refresh `repo` at `base` (default branch if None). Returns (path, base).

    The cache is ours: leftover changes from a previous run are discarded.
    """
    base = base or _api("GET", f"/repos/{repo}")["default_branch"]
    path = Path(config.get("WORKSPACE_DIR", "~/.cache/incident-agent")).expanduser() / repo
    if not (path / ".git").is_dir():
        path.parent.mkdir(parents=True, exist_ok=True)
        _git(path.parent, "clone", "--quiet", f"https://github.com/{repo}.git", path.name)
    _git(path, "fetch", "--quiet", "origin", base)
    _git(path, "reset", "--quiet", "--hard")
    _git(path, "clean", "-fdq")
    _git(path, "checkout", "--quiet", "-B", base, f"origin/{base}")
    return path, base

