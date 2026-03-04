"""Lightweight HTTP helpers for CLI commands that talk to the running API."""
from __future__ import annotations

import json
from typing import Any

import click

try:
    import httpx  # type: ignore[import-untyped]
except ImportError:
    httpx = None  # type: ignore[assignment]


DEFAULT_BASE_URL = "http://127.0.0.1:8088"


def client(base_url: str) -> "httpx.Client":
    """Return an httpx.Client with ``/api`` prefix.

    Falls back to urllib if httpx is not installed, but httpx is
    strongly recommended for interactive CLI use.
    """
    if httpx is None:
        raise ImportError(
            "httpx is required for CLI HTTP commands.  "
            "Install with:  pip install httpx",
        )
    base = base_url.rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    return httpx.Client(base_url=base, timeout=30.0)


def print_json(data: Any) -> None:
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))
