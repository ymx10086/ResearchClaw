"""Shared interactive prompt helpers used by CLI commands.

All terminal interaction with *questionary* is centralised here so that
the rest of the CLI code never imports questionary directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

try:
    import questionary  # type: ignore[import-untyped]

    _HAS_QUESTIONARY = True
except ImportError:
    _HAS_QUESTIONARY = False


def prompt_confirm(question: str, *, default: bool = False) -> bool:
    """Yes/No prompt.  Falls back to click.confirm without questionary."""
    if _HAS_QUESTIONARY:
        items = [
            questionary.Choice("Yes", value=True),
            questionary.Choice("No", value=False),
        ]
        preselect = items[0] if default else items[1]
        result = questionary.select(
            question,
            choices=items,
            default=preselect,
            use_shortcuts=False,
            use_arrow_keys=True,
            use_jk_keys=False,
        ).ask()
        if result is None:
            return default
        return result
    return click.confirm(question, default=default)


def prompt_path(label: str, *, default: str = "") -> str:
    """Ask for a filesystem path, warning if it doesn't exist."""
    while True:
        value = click.prompt(label, default=default, type=str)
        if not value:
            return value
        path = Path(value).expanduser()
        if path.exists():
            return str(path.resolve())
        if prompt_confirm(
            f"Path '{value}' does not exist, continue anyway?",
            default=True,
        ):
            return value


def prompt_choice(
    question: str,
    options: list[str],
    *,
    default: Optional[str] = None,
) -> str:
    """Let the user pick one item from a string list."""
    if _HAS_QUESTIONARY:
        items = [questionary.Choice(opt, value=opt) for opt in options]
        preselect = None
        if default is not None:
            try:
                idx = options.index(default)
                preselect = items[idx]
            except (ValueError, IndexError):
                pass
        result = questionary.select(
            question,
            choices=items,
            default=preselect,
            use_shortcuts=False,
            use_arrow_keys=True,
            use_jk_keys=False,
        ).ask()
        if result is None:
            return default or options[0]
        return result
    # Fallback: numbered list
    click.echo(question)
    for i, opt in enumerate(options, 1):
        marker = " *" if opt == default else ""
        click.echo(f"  {i}. {opt}{marker}")
    idx = click.prompt("Choice", type=int, default=1) - 1
    return options[max(0, min(idx, len(options) - 1))]


def prompt_select(
    question: str,
    options: list[tuple[str, str]],
    *,
    default: Optional[str] = None,
) -> Optional[str]:
    """Pick one from (label, value) pairs.  Returns value or None."""
    if _HAS_QUESTIONARY:
        items = [
            questionary.Choice(label, value=value) for label, value in options
        ]
        preselect = None
        if default is not None:
            for item in items:
                if item.value == default:
                    preselect = item
                    break
        return questionary.select(
            question,
            choices=items,
            default=preselect,
            use_shortcuts=False,
            use_arrow_keys=True,
            use_jk_keys=False,
        ).ask()
    click.echo(question)
    for i, (label, _) in enumerate(options, 1):
        click.echo(f"  {i}. {label}")
    idx = click.prompt("Choice", type=int, default=1) - 1
    idx = max(0, min(idx, len(options) - 1))
    return options[idx][1]


def prompt_checkbox(
    question: str,
    options: list[tuple[str, str]],
    *,
    checked: Optional[set[str]] = None,
    select_all_option: bool = True,
) -> Optional[list[str]]:
    """Multi-select checkbox.  Returns list of values or None."""
    if not _HAS_QUESTIONARY:
        # Fallback: comma-separated input
        click.echo(question)
        for i, (label, value) in enumerate(options, 1):
            mark = "x" if checked and value in checked else " "
            click.echo(f"  [{mark}] {i}. {label}")
        raw = click.prompt(
            "Enter numbers to select (comma-separated, or 'all')",
            default="all",
        )
        if raw.strip().lower() == "all":
            return [v for _, v in options]
        indices = [
            int(x.strip()) - 1 for x in raw.split(",") if x.strip().isdigit()
        ]
        return [options[i][1] for i in indices if 0 <= i < len(options)]

    _SELECT_ALL = "__select_all__"
    all_values = {v for _, v in options}
    current_checked = set(checked or set()) & all_values

    while True:
        all_currently_checked = (
            current_checked == all_values and len(all_values) > 0
        )
        items: list[questionary.Choice] = []
        if select_all_option:
            items.append(
                questionary.Choice(
                    "✦ Select All / Deselect All",
                    value=_SELECT_ALL,
                    checked=all_currently_checked,
                ),
            )
        for label, value in options:
            items.append(
                questionary.Choice(
                    label,
                    value=value,
                    checked=value in current_checked,
                ),
            )
        result = questionary.checkbox(
            question,
            choices=items,
            use_jk_keys=False,
        ).ask()
        if result is None:
            return None
        if _SELECT_ALL in result:
            current_checked = (
                set() if all_currently_checked else set(all_values)
            )
            continue
        return [r for r in result if r != _SELECT_ALL]
