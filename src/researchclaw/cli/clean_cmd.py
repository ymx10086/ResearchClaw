"""researchclaw clean — remove WORKING_DIR contents."""
from __future__ import annotations

import shutil
from pathlib import Path

import click

from ..constant import WORKING_DIR


def _iter_children(p: Path) -> list[Path]:
    if not p.exists():
        return []
    return sorted(list(p.iterdir()), key=lambda x: x.name)


@click.command("clean")
@click.option("--yes", is_flag=True, help="Do not prompt for confirmation")
@click.option(
    "--dry-run",
    is_flag=True,
    help="List what would be deleted, but do not delete",
)
def clean_cmd(yes: bool, dry_run: bool) -> None:
    """Clear ResearchClaw WORKING_DIR (~/.researchclaw by default)."""
    wd = Path(WORKING_DIR)

    if not wd.exists():
        click.echo(f"WORKING_DIR does not exist: {wd}")
        return

    children = _iter_children(wd)
    if not children:
        click.echo(f"WORKING_DIR is already empty: {wd}")
        return

    click.echo(f"WORKING_DIR: {wd}")
    click.echo("Will remove:")
    for c in children:
        click.echo(f"  - {c}")

    if dry_run:
        click.echo("dry-run: nothing deleted.")
        return

    if not yes:
        ok = click.confirm(f"Delete ALL contents under {wd}?", default=False)
        if not ok:
            click.echo("Cancelled.")
            return

    for c in children:
        try:
            if c.is_dir() and not c.is_symlink():
                shutil.rmtree(c)
            else:
                c.unlink()
        except FileNotFoundError:
            pass

    click.echo("Done.")
