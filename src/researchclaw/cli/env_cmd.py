"""CLI commands for environment variable management."""
from __future__ import annotations

import click

from ..envs import EnvStore


@click.group("env")
def env_group() -> None:
    """Manage environment variables."""


# ---------------------------------------------------------------
# list
# ---------------------------------------------------------------


@env_group.command("list")
def list_cmd() -> None:
    """List all environment variables."""
    store = EnvStore()
    items = store.list()
    if not items:
        click.echo("No environment variables configured.")
        return
    for profile in items:
        name = profile.get("name", "(unnamed)")
        click.echo(f"\n  Profile: {name}")
        click.echo(f"  {'─' * 50}")
        for key, val in sorted(profile.get("vars", {}).items()):
            click.echo(f"  {key:<30s}  {val}")
    click.echo()


# ---------------------------------------------------------------
# set
# ---------------------------------------------------------------


@env_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--profile",
    default="default",
    show_default=True,
    help="Profile name",
)
def set_cmd(key: str, value: str, profile: str) -> None:
    """Set an environment variable (KEY VALUE)."""
    store = EnvStore()
    item = store.get(profile) or {"name": profile, "vars": {}}
    item.setdefault("vars", {})[key] = value
    store.save(item)
    click.echo(f"✓ [{profile}] {key} = {value}")


# ---------------------------------------------------------------
# delete
# ---------------------------------------------------------------


@env_group.command("delete")
@click.argument("key")
@click.option(
    "--profile",
    default="default",
    show_default=True,
    help="Profile name",
)
def delete_cmd(key: str, profile: str) -> None:
    """Delete an environment variable."""
    store = EnvStore()
    item = store.get(profile)
    if not item or key not in item.get("vars", {}):
        click.echo(
            click.style(
                f"Env var '{key}' not found in profile '{profile}'.",
                fg="red",
            ),
        )
        raise SystemExit(1)
    del item["vars"][key]
    store.save(item)
    click.echo(f"✓ Deleted: {key} from [{profile}]")


# ---------------------------------------------------------------
# Interactive helper (used by init_cmd)
# ---------------------------------------------------------------


def configure_env_interactive() -> None:
    """Interactively add/edit environment variables."""
    from .utils import prompt_confirm

    store = EnvStore()
    profile_name = "default"

    while True:
        key = click.prompt(
            "  Variable name",
            default="",
            show_default=False,
        ).strip()
        if not key:
            break
        item = store.get(profile_name) or {"name": profile_name, "vars": {}}
        current = item.get("vars", {}).get(key, "")
        value = click.prompt(
            f"  Value for {key}",
            default=current or "",
            show_default=bool(current),
        )
        item.setdefault("vars", {})[key] = value
        store.save(item)
        click.echo(f"  ✓ {key} = {value}")
        if not prompt_confirm("Add another variable?", default=False):
            break
    click.echo("Environment variable configuration complete.")
