"""CLI commands for managing chats via HTTP API (/chats)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .http import client, print_json
from ..app.channels.schema import DEFAULT_CHANNEL


def _base_url(ctx: click.Context, base_url: Optional[str]) -> str:
    if base_url:
        return base_url.rstrip("/")
    host = (ctx.obj or {}).get("host", "127.0.0.1")
    port = (ctx.obj or {}).get("port", 8088)
    return f"http://{host}:{port}"


@click.group("chats")
def chats_group() -> None:
    """Manage chat sessions via the HTTP API (/chats).

    \b
    Examples:
      researchclaw chats list
      researchclaw chats list --user-id alice
      researchclaw chats get <chat_id>
      researchclaw chats create --session-id s1 --user-id u1
      researchclaw chats delete <chat_id>
    """


@chats_group.command("list")
@click.option("--user-id", default=None, help="Filter by user ID")
@click.option("--channel", default=None, help="Filter by channel")
@click.option("--base-url", default=None, help="Override API base URL")
@click.pass_context
def list_chats(
    ctx: click.Context,
    user_id: Optional[str],
    channel: Optional[str],
    base_url: Optional[str],
) -> None:
    """List all chats, optionally filtered."""
    base_url = _base_url(ctx, base_url)
    params: dict[str, str] = {}
    if user_id:
        params["user_id"] = user_id
    if channel:
        params["channel"] = channel
    with client(base_url) as c:
        r = c.get("/chats", params=params)
        r.raise_for_status()
        print_json(r.json())


@chats_group.command("get")
@click.argument("chat_id")
@click.option("--base-url", default=None, help="Override API base URL")
@click.pass_context
def get_chat(
    ctx: click.Context,
    chat_id: str,
    base_url: Optional[str],
) -> None:
    """View details of a specific chat."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.get(f"/chats/{chat_id}")
        if r.status_code == 404:
            raise click.ClickException(f"chat not found: {chat_id}")
        r.raise_for_status()
        print_json(r.json())


@chats_group.command("create")
@click.option(
    "-f",
    "--file",
    "file_",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Create from JSON file",
)
@click.option("--name", default="New Chat", help="Chat name")
@click.option("--session-id", default=None, help="Session identifier")
@click.option("--user-id", default=None, help="User ID")
@click.option(
    "--channel",
    default=DEFAULT_CHANNEL,
    help=f"Channel name (default {DEFAULT_CHANNEL})",
)
@click.option("--base-url", default=None, help="Override API base URL")
@click.pass_context
def create_chat(
    ctx: click.Context,
    file_: Optional[Path],
    name: str,
    session_id: Optional[str],
    user_id: Optional[str],
    channel: str,
    base_url: Optional[str],
) -> None:
    """Create a new chat."""
    base_url = _base_url(ctx, base_url)
    if file_ is not None:
        payload = json.loads(file_.read_text(encoding="utf-8"))
    else:
        if not session_id:
            raise click.UsageError(
                "--session-id is required for inline creation",
            )
        if not user_id:
            raise click.UsageError("--user-id is required for inline creation")
        payload = {
            "id": "",
            "name": name,
            "session_id": session_id,
            "user_id": user_id,
            "channel": channel,
            "meta": {},
        }
    with client(base_url) as c:
        r = c.post("/chats", json=payload)
        r.raise_for_status()
        print_json(r.json())


@chats_group.command("update")
@click.argument("chat_id")
@click.option("--name", required=True, help="New chat name")
@click.option("--base-url", default=None, help="Override API base URL")
@click.pass_context
def update_chat(
    ctx: click.Context,
    chat_id: str,
    name: str,
    base_url: Optional[str],
) -> None:
    """Update chat name."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.get("/chats")
        r.raise_for_status()
        specs = r.json()
    payload = next((s for s in specs if s.get("id") == chat_id), None)
    if payload is None:
        raise click.ClickException(f"chat not found: {chat_id}")
    payload["name"] = name
    with client(base_url) as c:
        r = c.put(f"/chats/{chat_id}", json=payload)
        r.raise_for_status()
        print_json(r.json())


@chats_group.command("delete")
@click.argument("chat_id")
@click.option("--base-url", default=None, help="Override API base URL")
@click.pass_context
def delete_chat(
    ctx: click.Context,
    chat_id: str,
    base_url: Optional[str],
) -> None:
    """Delete a specific chat."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.delete(f"/chats/{chat_id}")
        if r.status_code == 404:
            raise click.ClickException(f"chat not found: {chat_id}")
        r.raise_for_status()
        print_json(r.json())
