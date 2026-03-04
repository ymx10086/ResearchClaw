"""researchclaw uninstall — remove the environment and CLI wrapper."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import click

from ..constant import WORKING_DIR

_INSTALLER_DIRS = ("venv", "bin")

_SHELL_PROFILES = (
    Path.home() / ".zshrc",
    Path.home() / ".bashrc",
    Path.home() / ".bash_profile",
)


def _remove_path_entry(profile: Path) -> bool:
    """Remove ResearchClaw PATH lines from a shell profile."""
    if not profile.is_file():
        return False
    text = profile.read_text()
    cleaned = re.sub(
        r"\n?# ResearchClaw\nexport PATH=\"\$HOME/\.researchclaw/bin:\$PATH\"\n?",
        "\n",
        text,
    )
    if cleaned == text:
        return False
    profile.write_text(cleaned)
    return True


@click.command("uninstall")
@click.option(
    "--purge",
    is_flag=True,
    help="Also remove all data (config, models, etc.)",
)
@click.option("--yes", is_flag=True, help="Do not prompt for confirmation")
def uninstall_cmd(purge: bool, yes: bool) -> None:
    """Remove ResearchClaw environment, CLI wrapper, and shell PATH entries."""
    wd = Path(WORKING_DIR)

    if purge:
        click.echo(f"This will remove ALL ResearchClaw data in {wd}")
    else:
        click.echo(
            "This will remove the ResearchClaw Python environment and CLI wrapper.",
        )
        click.echo(f"Your configuration and data in {wd} will be preserved.")

    if not yes:
        ok = click.confirm("Continue?", default=False)
        if not ok:
            click.echo("Cancelled.")
            return

    for dirname in _INSTALLER_DIRS:
        d = wd / dirname
        if d.exists():
            shutil.rmtree(d)
            click.echo(f"  Removed {d}")

    if purge and wd.exists():
        shutil.rmtree(wd)
        click.echo(f"  Removed {wd}")

    for profile in _SHELL_PROFILES:
        if _remove_path_entry(profile):
            click.echo(f"  Cleaned {profile}")

    click.echo("")
    click.echo("ResearchClaw uninstalled. Please restart your terminal.")
