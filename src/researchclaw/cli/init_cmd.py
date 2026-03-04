# flake8: noqa: E501
"""CLI init: interactively create working_dir config and research profile."""
from __future__ import annotations

from pathlib import Path

import click

from .env_cmd import configure_env_interactive
from .providers_cmd import configure_providers_interactive
from .skills_cmd import configure_skills_interactive
from .utils import prompt_confirm, prompt_choice
from ..config import load_config, save_config
from ..constant import (
    EXAMPLES_DIR,
    EXPERIMENTS_DIR,
    MD_FILES_DIR,
    PAPERS_DIR,
    REFERENCES_DIR,
    WORKING_DIR,
)

SECURITY_WARNING = """
Security warning — please read.

ResearchClaw is a research assistant that runs in your own environment. It can
connect to channels, read files, run commands, call external APIs, and manage
your research data. By default it is a single-operator boundary.

Recommended baseline:
- Restrict which channels and users can trigger the agent.
- Run skills with least privilege; sandbox where you can.
- Keep secrets out of the agent's working directory.
- Use a capable model when the agent has tools or handles untrusted input.
- Review your config and skills regularly.
"""

DEFAULT_HEARTBEAT_MDS = {
    "zh": """# 心跳检查清单
- 检查新论文推送通知
- 查看实验进度
- 检查待办事项
- 若安静超过 8h，轻量 check-in
""",
    "en": """# Heartbeat checklist
- Check new paper notifications
- Review experiment progress
- Check tasks for blockers
- Light check-in if quiet for 8h
""",
}


def _echo_security_warning() -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel

        Console().print(
            Panel(
                SECURITY_WARNING.strip(),
                title="[bold]🔬 Security warning — please read[/bold]",
                border_style="blue",
            ),
        )
    except ImportError:
        click.echo(SECURITY_WARNING)


@click.command("init")
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing config if present.",
)
@click.option(
    "--defaults",
    "use_defaults",
    is_flag=True,
    help="Use defaults only, no interactive prompts.",
)
@click.option(
    "--accept-security",
    "accept_security",
    is_flag=True,
    help="Skip security confirmation.",
)
def init_cmd(force: bool, use_defaults: bool, accept_security: bool) -> None:
    """Create working dir with config and research profile (interactive)."""
    wd = Path(WORKING_DIR)
    config_path = wd / "config.json"
    heartbeat_path = wd / "HEARTBEAT.md"

    click.echo(f"Working dir: {wd}")

    # --- Security warning ---
    _echo_security_warning()
    if use_defaults and accept_security:
        click.echo(
            "Security acceptance assumed (--accept-security with --defaults).",
        )
    else:
        accepted = prompt_confirm(
            "Have you read and accepted the security notice above?",
            default=True,
        )
        if not accepted:
            click.echo("Initialization aborted.")
            raise click.Abort()

    # --- Create directories ---
    for rel in [
        PAPERS_DIR,
        REFERENCES_DIR,
        EXPERIMENTS_DIR,
        MD_FILES_DIR,
        EXAMPLES_DIR,
    ]:
        (wd / rel).mkdir(parents=True, exist_ok=True)

    # --- Research profile ---
    profile = wd / "PROFILE.md"
    if not profile.exists() or force:
        if use_defaults:
            content = (
                "# Research Profile\n\n"
                "- Name: \n"
                "- Institution: \n"
                "- Research Areas: \n"
            )
        else:
            click.echo("\n=== Research Profile ===")
            name = click.prompt("Your name", default="").strip()
            institution = click.prompt("Institution", default="").strip()
            areas = click.prompt(
                "Research areas (comma-separated)",
                default="",
            ).strip()
            content = (
                "# Research Profile\n\n"
                f"- Name: {name}\n"
                f"- Institution: {institution}\n"
                f"- Research Areas: {areas}\n"
            )
        profile.write_text(content, encoding="utf-8")
        click.echo(f"✓ Research profile saved to {profile}")

    # --- config.json ---
    write_config = True
    if config_path.is_file() and not force and not use_defaults:
        write_config = prompt_confirm(
            f"{config_path} exists. Overwrite?",
            default=False,
        )

    if not write_config:
        click.echo("Skipping configuration.")
    else:
        config = load_config() if config_path.is_file() else {}

        if not use_defaults:
            # Language selection
            language = prompt_choice(
                "Select language for MD files:",
                options=["en", "zh"],
                default=config.get("language", "en"),
            )
            config["language"] = language

            # Show tool details
            config["show_tool_details"] = prompt_confirm(
                "Show tool call/result details in channel messages?",
                default=config.get("show_tool_details", True),
            )

            # Heartbeat configuration
            click.echo("\n=== Heartbeat Configuration ===")
            every = click.prompt(
                "Heartbeat interval (e.g. 30m, 1h)",
                default=config.get("heartbeat_every", "1h"),
                type=str,
            ).strip()
            config["heartbeat_every"] = every

            # Paper digest configuration
            click.echo("\n=== Paper Digest Configuration ===")
            digest_enabled = prompt_confirm(
                "Enable daily paper digest?",
                default=config.get("paper_digest_enabled", False),
            )
            config["paper_digest_enabled"] = digest_enabled
            if digest_enabled:
                digest_hour = click.prompt(
                    "Digest hour (0-23)",
                    default=config.get("paper_digest_hour", 8),
                    type=int,
                )
                config["paper_digest_hour"] = digest_hour
                topics = click.prompt(
                    "Research topics for digest (comma-separated)",
                    default=config.get("paper_digest_topics", ""),
                ).strip()
                config["paper_digest_topics"] = topics
        else:
            config.setdefault("language", "en")
            config.setdefault("show_tool_details", True)
            config.setdefault("heartbeat_every", "1h")

        save_config(config)
        click.echo(f"\n✓ Configuration saved to {config_path}")

    # --- LLM provider ---
    from ..providers import ProviderStore

    store = ProviderStore()
    has_provider = bool(store.list_providers())

    if has_provider:
        click.echo("\n✓ LLM provider(s) already configured.")
        if not use_defaults and prompt_confirm(
            "Reconfigure LLM provider?",
            default=False,
        ):
            configure_providers_interactive(use_defaults=False)
    else:
        click.echo("\n=== LLM Provider Configuration (required) ===")
        configure_providers_interactive(use_defaults=use_defaults)

    # --- Skills ---
    if use_defaults:
        from ..agents.skills_manager import sync_skills_to_working_dir

        click.echo("Enabling all skills by default...")
        synced = sync_skills_to_working_dir(skill_names=None, force=False)
        click.echo(f"✓ Skills synced: {synced}")
    elif write_config:
        skills_choice = prompt_choice(
            "Configure skills:",
            options=["all", "none", "custom"],
            default="all",
        )
        if skills_choice == "all":
            from ..agents.skills_manager import sync_skills_to_working_dir

            click.echo("Enabling all skills...")
            synced = sync_skills_to_working_dir(skill_names=None, force=False)
            click.echo(f"✓ Skills synced: {synced}")
        elif skills_choice == "custom":
            configure_skills_interactive()
        else:
            click.echo("Skipped skills configuration.")

    # --- Environment variables ---
    if not use_defaults:
        if prompt_confirm("Configure environment variables?", default=False):
            configure_env_interactive()
        else:
            click.echo("Skipped environment variable configuration.")

    # --- MD files ---
    config = load_config() if config_path.is_file() else {}
    language = config.get("language", "en")
    try:
        from ..agents.utils import copy_md_files

        if use_defaults:
            click.echo(f"\nChecking MD files [language: {language}]...")
            copied = copy_md_files(language, skip_existing=True)
            if copied:
                click.echo(
                    f"✓ Copied {len(copied)} md file(s): {', '.join(copied)}",
                )
            else:
                click.echo("✓ MD files already present, skipped.")
        else:
            copied = copy_md_files(language)
            if copied:
                click.echo(
                    f"✓ Copied {len(copied)} md file(s): {', '.join(copied)}",
                )
    except (ImportError, Exception):
        pass  # copy_md_files may not exist yet

    # --- HEARTBEAT.md ---
    write_heartbeat = True
    if heartbeat_path.is_file() and not force:
        if use_defaults:
            click.echo("✓ HEARTBEAT.md already present, skipped.")
            write_heartbeat = False
        else:
            write_heartbeat = prompt_confirm(
                f"{heartbeat_path} exists. Overwrite?",
                default=False,
            )

    if write_heartbeat:
        hb_content = DEFAULT_HEARTBEAT_MDS.get(
            language,
            DEFAULT_HEARTBEAT_MDS["en"],
        )
        if not use_defaults:
            click.echo("\n=== Heartbeat Query Configuration ===")
            if prompt_confirm(
                "Edit heartbeat query in your default editor?",
                default=True,
            ):
                edited = click.edit(
                    hb_content,
                    extension=".md",
                    require_save=False,
                )
                if edited is not None:
                    hb_content = edited
        heartbeat_path.write_text(hb_content.strip() + "\n", encoding="utf-8")
        click.echo(f"✓ Heartbeat query saved to {heartbeat_path}")

    click.echo("\n✓ Initialization complete!")
