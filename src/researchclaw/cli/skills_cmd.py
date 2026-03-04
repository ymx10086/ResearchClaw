"""CLI skill: list and interactively enable/disable skills."""
from __future__ import annotations

import click

from ..agents.skills_manager import SkillsManager, list_active_skills
from .utils import prompt_checkbox, prompt_confirm


# pylint: disable=too-many-branches
def configure_skills_interactive() -> None:
    """Interactively select which skills to enable (multi-select)."""
    manager = SkillsManager()
    all_skills = manager.list_all_skills()
    if not all_skills:
        click.echo("No skills found. Nothing to configure.")
        return

    active = set(list_active_skills())
    all_names = {s.name for s in all_skills}

    default_checked = active if active else all_names

    options: list[tuple[str, str]] = []
    for skill in sorted(all_skills, key=lambda s: s.name):
        status = "✓" if skill.name in active else "✗"
        label = f"{skill.name}  [{status}] ({skill.source})"
        options.append((label, skill.name))

    click.echo("\n=== Skills Configuration ===")
    click.echo("Use ↑/↓ to move, <space> to toggle, <enter> to confirm.\n")

    selected = prompt_checkbox(
        "Select skills to enable:",
        options=options,
        checked=default_checked,
        select_all_option=False,
    )

    if selected is None:
        click.echo("\n\nOperation cancelled.")
        return

    selected_set = set(selected)
    to_enable = selected_set - active
    to_disable = (all_names & active) - selected_set

    if not to_enable and not to_disable:
        click.echo("\nNo changes needed.")
        return

    click.echo()
    if to_enable:
        click.echo(
            click.style(
                f"  + Enable:  {', '.join(sorted(to_enable))}",
                fg="green",
            ),
        )
    if to_disable:
        click.echo(
            click.style(
                f"  - Disable: {', '.join(sorted(to_disable))}",
                fg="red",
            ),
        )

    save = prompt_confirm("Apply changes?", default=True)
    if not save:
        click.echo("Skipped. No changes applied.")
        return

    for name in to_enable:
        result = manager.enable_skill(name)
        if result:
            click.echo(f"  ✓ Enabled: {name}")
        else:
            click.echo(click.style(f"  ✗ Failed to enable: {name}", fg="red"))

    for name in to_disable:
        result = manager.disable_skill(name)
        if result:
            click.echo(f"  ✓ Disabled: {name}")
        else:
            click.echo(click.style(f"  ✗ Failed to disable: {name}", fg="red"))

    click.echo("\n✓ Skills configuration updated!")


@click.group("skills")
def skills_group() -> None:
    """Manage skills (list / configure)."""


@skills_group.command("list")
def list_cmd() -> None:
    """Show all skills and their enabled/disabled status."""
    manager = SkillsManager()
    all_skills = manager.list_all_skills()
    active = set(list_active_skills())

    if not all_skills:
        click.echo("No skills found.")
        return

    click.echo(f"\n{'─' * 50}")
    click.echo(f"  {'Skill Name':<30s} {'Source':<12s} Status")
    click.echo(f"{'─' * 50}")

    for skill in sorted(all_skills, key=lambda s: s.name):
        status = (
            click.style("✓ enabled", fg="green")
            if skill.name in active
            else click.style("✗ disabled", fg="red")
        )
        click.echo(f"  {skill.name:<30s} {skill.source:<12s} {status}")

    click.echo(f"{'─' * 50}")
    enabled_count = sum(1 for s in all_skills if s.name in active)
    click.echo(
        f"  Total: {len(all_skills)} skills, "
        f"{enabled_count} enabled, "
        f"{len(all_skills) - enabled_count} disabled\n",
    )


@skills_group.command("config")
def configure_cmd() -> None:
    """Interactively select which skills to enable."""
    configure_skills_interactive()
