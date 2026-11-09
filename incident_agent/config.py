"""Settings come from the process environment or a .env file in the current directory."""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv


def load_env() -> None:
    """Load .env from the current directory (or a parent). Real env vars win."""
    load_dotenv(find_dotenv(usecwd=True))


def get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or default


def require(name: str) -> str:
    value = get(name)
    if not value:
        raise ValueError(f"{name} is not set. Add it to .env (see sample.env).")
    return value
