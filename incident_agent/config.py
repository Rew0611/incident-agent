"""Settings come from the process environment or a .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

CHECKOUT_ENV = Path(__file__).resolve().parent.parent / ".env"


def load_env() -> None:
    """Load .env from the current directory (or a parent), then from this checkout.

    Existing env vars always win, so the first file to set a value wins too.
    """
    load_dotenv(find_dotenv(usecwd=True))
    load_dotenv(CHECKOUT_ENV)


def get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or default


def require(name: str) -> str:
    value = get(name)
    if not value:
        raise ValueError(f"{name} is not set. Add it to .env (see sample.env).")
    return value
