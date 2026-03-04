"""CLI commands for managing LLM providers and local models."""
from __future__ import annotations

from typing import Optional

import click

from ..providers import ProviderStore
from .utils import prompt_choice


def _mask_api_key(key: str) -> str:
    """Mask an API key, keeping first 4 chars visible."""
    if not key:
        return "(not set)"
    if len(key) <= 4:
        return "****"
    return key[:4] + "****"


def configure_provider_api_key_interactive(
    provider_name: str | None = None,
) -> str:
    """Interactively configure a provider's API key. Returns provider name."""
    store = ProviderStore()
    providers = store.list_providers()

    if provider_name is None:
        if providers:
            names = [p["name"] for p in providers]
            names.append("(add new)")
            provider_name = prompt_choice("Select provider:", options=names)
            if provider_name == "(add new)":
                provider_name = click.prompt("Provider name").strip()
        else:
            provider_name = click.prompt("Provider name").strip()

    existing = next(
        (p for p in providers if p["name"] == provider_name),
        None,
    )
    current_key = existing.get("api_key", "") if existing else ""
    current_url = existing.get("base_url", "") if existing else ""
    current_type = (
        existing.get("provider_type", "openai") if existing else "openai"
    )

    provider_type = click.prompt(
        "Provider type (openai/anthropic/dashscope/deepseek/ollama/custom)",
        default=current_type,
    ).strip()

    if provider_type not in ("ollama",):
        api_key = click.prompt(
            "API key",
            default=current_key or "",
            hide_input=True,
            show_default=False,
            prompt_suffix=f" [{'set' if current_key else 'not set'}]: ",
        )
    else:
        api_key = ""

    base_url = click.prompt(
        "Base URL (leave empty for default)",
        default=current_url or "",
        show_default=bool(current_url),
    ).strip()

    model_name = click.prompt(
        "Default model name",
        default=(existing or {}).get("model_name", ""),
    ).strip()

    store.save_provider(
        {
            "name": provider_name,
            "provider_type": provider_type,
            "model_name": model_name,
            "api_key": api_key,
            "base_url": base_url,
            "extra": {},
        },
    )

    click.echo(
        f"✓ {provider_name} — API Key: {_mask_api_key(api_key)}"
        + (f", Base URL: {base_url}" if base_url else ""),
    )
    return provider_name


def configure_providers_interactive(*, use_defaults: bool = False) -> None:
    """Full interactive flow: configure provider → set active."""
    if use_defaults:
        click.echo(
            "Using default provider settings. Run 'researchclaw models config' to change.",
        )
        return

    click.echo("\n--- Provider Configuration ---")
    while True:
        configure_provider_api_key_interactive()
        if not click.confirm("Configure another provider?", default=False):
            break


@click.group("models")
def models_group() -> None:
    """Manage LLM models and provider configuration."""


@models_group.command("list")
def list_cmd() -> None:
    """Show all providers and their current configuration."""
    store = ProviderStore()
    providers = store.list_providers()

    if not providers:
        click.echo("No providers configured.")
        click.echo("Run 'researchclaw models config' to add one.")
        return

    click.echo("\n=== Providers ===")
    for p in providers:
        click.echo(f"\n{'─' * 44}")
        click.echo(f"  {p['name']} ({p['provider_type']})")
        click.echo(f"{'─' * 44}")
        click.echo(f"  {'api_key':16s}: {_mask_api_key(p.get('api_key', ''))}")
        if p.get("base_url"):
            click.echo(f"  {'base_url':16s}: {p['base_url']}")
        if p.get("model_name"):
            click.echo(f"  {'model':16s}: {p['model_name']}")
    click.echo()


@models_group.command("config")
def config_cmd() -> None:
    """Interactively configure providers and active models."""
    configure_providers_interactive()


@models_group.command("add")
@click.argument("name")
@click.option("--type", "provider_type", required=True, help="Provider type")
@click.option("--model", "model_name", default="", help="Model name")
@click.option("--api-key", default="", help="API key")
@click.option("--base-url", default="", help="Base URL")
def add_cmd(
    name: str,
    provider_type: str,
    model_name: str,
    api_key: str,
    base_url: str,
) -> None:
    """Add or update a provider."""
    store = ProviderStore()
    store.save_provider(
        {
            "name": name,
            "provider_type": provider_type,
            "model_name": model_name,
            "api_key": api_key,
            "base_url": base_url,
            "extra": {},
        },
    )
    click.echo(f"✓ Provider '{name}' saved.")


@models_group.command("remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def remove_cmd(name: str, yes: bool) -> None:
    """Remove a provider."""
    if not yes:
        if not click.confirm(f"Delete provider '{name}'?"):
            return
    store = ProviderStore()
    try:
        store.remove_provider(name)
    except KeyError:
        click.echo(click.style(f"Provider not found: {name}", fg="red"))
        raise SystemExit(1)
    click.echo(f"✓ Provider '{name}' removed.")


# ---------------------------------------------------------------------------
# Local model management commands
# ---------------------------------------------------------------------------


@models_group.command("download")
@click.argument("repo_id")
@click.option(
    "--file",
    "-f",
    "filename",
    default=None,
    help="Specific file to download",
)
@click.option(
    "--backend",
    "-b",
    type=click.Choice(["llamacpp", "mlx"]),
    default="llamacpp",
    help="Target backend",
)
@click.option(
    "--source",
    "-s",
    type=click.Choice(["huggingface", "modelscope"]),
    default="huggingface",
    help="Download source",
)
def download_cmd(
    repo_id: str,
    filename: str | None,
    backend: str,
    source: str,
) -> None:
    """Download a model from Hugging Face Hub or ModelScope.

    \b
    Examples:
      researchclaw models download TheBloke/Mistral-7B-Instruct-v0.2-GGUF
      researchclaw models download Qwen/Qwen3-8B-GGUF -f qwen3-8b.Q4_K_M.gguf
    """
    try:
        from ..local_models import (
            LocalModelManager,
            BackendType,
            DownloadSource,
        )
    except ImportError as exc:
        click.echo(
            click.style(
                "Local model dependencies not installed. "
                "Install with: pip install 'researchclaw[local]'",
                fg="red",
            ),
        )
        raise SystemExit(1) from exc

    backend_type = BackendType(backend)
    source_type = DownloadSource(source)
    suffix = f" ({filename})" if filename else ""
    click.echo(f"Downloading {repo_id}{suffix} from {source}...")

    try:
        info = LocalModelManager.download_model_sync(
            repo_id=repo_id,
            filename=filename,
            backend=backend_type,
            source=source_type,
        )
    except Exception as exc:
        click.echo(click.style(f"Download failed: {exc}", fg="red"))
        raise SystemExit(1) from exc

    size_mb = info.file_size / (1024 * 1024)
    click.echo(f"Done! Model saved to: {info.local_path}")
    click.echo(f"  Size: {size_mb:.1f} MB")
    click.echo(f"  ID: {info.id}")
    click.echo(f"  Backend: {info.backend.value}")


@models_group.command("local")
@click.option(
    "--backend",
    "-b",
    type=click.Choice(["llamacpp", "mlx"]),
    default=None,
    help="Filter by backend",
)
def list_local_cmd(backend: str | None) -> None:
    """List all downloaded local models."""
    try:
        from ..local_models import list_local_models, BackendType
    except ImportError:
        click.echo(
            "Local model support not installed. Install with: pip install 'researchclaw[local]'",
        )
        return

    backend_type = BackendType(backend) if backend else None
    models = list_local_models(backend=backend_type)

    if not models:
        click.echo("No local models downloaded.")
        click.echo(
            "Use 'researchclaw models download <repo_id>' to download one.",
        )
        return

    click.echo(f"\n=== Local Models ({len(models)}) ===")
    for m in models:
        size_mb = m.file_size / (1024 * 1024)
        click.echo(f"\n{'─' * 44}")
        click.echo(f"  {m.display_name}")
        click.echo(f"  ID:      {m.id}")
        click.echo(f"  Backend: {m.backend.value}")
        click.echo(f"  Source:  {m.source.value}")
        click.echo(f"  Size:    {size_mb:.1f} MB")
        click.echo(f"  Path:    {m.local_path}")
    click.echo()


@models_group.command("remove-local")
@click.argument("model_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def remove_local_cmd(model_id: str, yes: bool) -> None:
    """Remove a downloaded local model."""
    try:
        from ..local_models import delete_local_model
    except ImportError as exc:
        click.echo(
            click.style(
                "Local model support not installed.",
                fg="red",
            ),
        )
        raise SystemExit(1) from exc

    if not yes:
        if not click.confirm(f"Delete local model '{model_id}'?"):
            return
    try:
        delete_local_model(model_id)
    except ValueError as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"))
        raise SystemExit(1) from exc
    click.echo(f"Done! Model '{model_id}' deleted.")
