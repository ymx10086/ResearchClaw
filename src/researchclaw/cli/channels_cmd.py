"""CLI channel: list and interactively configure channels in config.json."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import click

from ..config import load_config, save_config
from ..constant import CUSTOM_CHANNELS_DIR, WORKING_DIR
from .utils import prompt_confirm, prompt_select

# Fields that contain secrets — display masked in ``list``
_SECRET_FIELDS = {
    "bot_token",
    "client_secret",
    "app_secret",
    "http_proxy_auth",
    "api_key",
    "twilio_auth_token",
}

_ALL_CHANNEL_NAMES = {
    "console": "Console",
    "telegram": "Telegram",
    "discord": "Discord",
    "dingtalk": "DingTalk",
    "feishu": "Feishu",
    "imessage": "iMessage",
    "qq": "QQ",
    "voice": "Voice",
}

CHANNEL_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Custom channel: {key}. Edit and implement required methods."""
from __future__ import annotations

from typing import Any

from researchclaw.app.channels.base import BaseChannel
from researchclaw.app.channels.schema import ChannelType


class CustomChannel(BaseChannel):
    channel: ChannelType = "{key}"

    def __init__(self, process, enabled=True, bot_prefix="", on_reply_sent=None, show_tool_details=True, **kwargs):
        super().__init__(process, on_reply_sent=on_reply_sent, show_tool_details=show_tool_details)
        self.enabled = enabled
        self.bot_prefix = bot_prefix or ""

    @classmethod
    def from_config(cls, process, config, on_reply_sent=None, show_tool_details=True):
        return cls(
            process=process,
            enabled=getattr(config, "enabled", True),
            bot_prefix=getattr(config, "bot_prefix", ""),
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )

    @classmethod
    def from_env(cls, process, on_reply_sent=None):
        return cls(process=process, on_reply_sent=on_reply_sent)

    def build_agent_request_from_native(self, native_payload: Any):
        payload = native_payload if isinstance(native_payload, dict) else {{}}
        channel_id = payload.get("channel_id") or self.channel
        sender_id = payload.get("sender_id") or ""
        meta = payload.get("meta") or {{}}
        session_id = self.resolve_session_id(sender_id, meta)
        text = payload.get("text", "")
        from agentscope_runtime.engine.schemas.agent_schemas import TextContent, ContentType
        content_parts = [TextContent(type=ContentType.TEXT, text=text)]
        request = self.build_agent_request_from_user_content(
            channel_id=channel_id, sender_id=sender_id, session_id=session_id,
            content_parts=content_parts, channel_meta=meta,
        )
        request.channel_meta = meta
        return request

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send(self, to_handle: str, text: str, meta=None):
        pass
'''


def _mask(value: str) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 4:
        return "****"
    return value[:4] + "****"


# ── per-channel interactive configurators ──────────────────────────


def _configure_generic(name: str, current: dict) -> dict:
    """Generic channel configurator: enabled + bot_prefix + any extra fields."""
    click.echo(f"\n=== Configure {name} Channel ===")
    current["enabled"] = prompt_confirm(
        f"Enable {name} channel?",
        default=current.get("enabled", False),
    )
    if not current["enabled"]:
        return current
    current["bot_prefix"] = click.prompt(
        "Bot prefix (e.g., [BOT])",
        default=current.get("bot_prefix", "[BOT]"),
        type=str,
    )
    return current


def _configure_discord(current: dict) -> dict:
    click.echo("\n=== Configure Discord Channel ===")
    current["enabled"] = prompt_confirm(
        "Enable Discord?",
        default=current.get("enabled", False),
    )
    if not current["enabled"]:
        return current
    current["bot_prefix"] = click.prompt(
        "Bot prefix",
        default=current.get("bot_prefix", "[BOT]"),
        type=str,
    )
    current["bot_token"] = click.prompt(
        "Discord Bot Token",
        default=current.get("bot_token", ""),
        hide_input=True,
        type=str,
    )
    use_proxy = prompt_confirm(
        "Use HTTP proxy?",
        default=bool(current.get("http_proxy")),
    )
    if use_proxy:
        current["http_proxy"] = click.prompt(
            "HTTP proxy address",
            default=current.get("http_proxy", ""),
            type=str,
        )
    else:
        current["http_proxy"] = ""
    return current


def _configure_dingtalk(current: dict) -> dict:
    click.echo("\n=== Configure DingTalk Channel ===")
    current["enabled"] = prompt_confirm(
        "Enable DingTalk?",
        default=current.get("enabled", False),
    )
    if not current["enabled"]:
        return current
    current["bot_prefix"] = click.prompt(
        "Bot prefix",
        default=current.get("bot_prefix", "[BOT]"),
        type=str,
    )
    current["client_id"] = click.prompt(
        "DingTalk Client ID",
        default=current.get("client_id", ""),
        type=str,
    )
    current["client_secret"] = click.prompt(
        "DingTalk Client Secret",
        default=current.get("client_secret", ""),
        hide_input=True,
        type=str,
    )
    return current


def _configure_feishu(current: dict) -> dict:
    click.echo("\n=== Configure Feishu Channel ===")
    current["enabled"] = prompt_confirm(
        "Enable Feishu?",
        default=current.get("enabled", False),
    )
    if not current["enabled"]:
        return current
    current["bot_prefix"] = click.prompt(
        "Bot prefix",
        default=current.get("bot_prefix", "[BOT]"),
        type=str,
    )
    current["app_id"] = click.prompt(
        "Feishu App ID",
        default=current.get("app_id", ""),
        type=str,
    )
    current["app_secret"] = click.prompt(
        "Feishu App Secret",
        default=current.get("app_secret", ""),
        hide_input=True,
        type=str,
    )
    return current


def _configure_telegram(current: dict) -> dict:
    click.echo("\n=== Configure Telegram Channel ===")
    current["enabled"] = prompt_confirm(
        "Enable Telegram?",
        default=current.get("enabled", False),
    )
    if not current["enabled"]:
        return current
    current["bot_prefix"] = click.prompt(
        "Bot prefix",
        default=current.get("bot_prefix", "[BOT]"),
        type=str,
    )
    current["bot_token"] = click.prompt(
        "Telegram Bot Token",
        default=current.get("bot_token", ""),
        hide_input=True,
        type=str,
    )
    use_proxy = prompt_confirm(
        "Use HTTP proxy?",
        default=bool(current.get("http_proxy")),
    )
    if use_proxy:
        current["http_proxy"] = click.prompt(
            "HTTP proxy address",
            default=current.get("http_proxy", ""),
            type=str,
        )
    else:
        current["http_proxy"] = ""
    return current


def _configure_voice(current: dict) -> dict:
    click.echo("\n=== Configure Voice Channel (Twilio) ===")
    current["enabled"] = prompt_confirm(
        "Enable Voice?",
        default=current.get("enabled", False),
    )
    if not current["enabled"]:
        return current
    current["bot_prefix"] = click.prompt(
        "Bot prefix",
        default=current.get("bot_prefix", "[BOT]"),
        type=str,
    )
    current["public_base_url"] = click.prompt(
        "Public base URL (https://your-domain)",
        default=current.get("public_base_url", ""),
        type=str,
    )
    current["phone_number"] = click.prompt(
        "Twilio phone number (optional label)",
        default=current.get("phone_number", ""),
        type=str,
    )
    current["phone_number_sid"] = click.prompt(
        "Twilio phone_number_sid",
        default=current.get("phone_number_sid", ""),
        type=str,
    )
    current["twilio_account_sid"] = click.prompt(
        "Twilio account SID",
        default=current.get("twilio_account_sid", ""),
        type=str,
    )
    current["twilio_auth_token"] = click.prompt(
        "Twilio auth token",
        default=current.get("twilio_auth_token", ""),
        hide_input=True,
        type=str,
    )
    current["welcome_greeting"] = click.prompt(
        "Welcome greeting",
        default=current.get(
            "welcome_greeting",
            "Hi! This is ResearchClaw. How can I help you?",
        ),
        type=str,
    )
    return current


_CHANNEL_CONFIGURATORS = {
    "console": ("Console", lambda c: _configure_generic("Console", c)),
    "telegram": ("Telegram", _configure_telegram),
    "discord": ("Discord", _configure_discord),
    "dingtalk": ("DingTalk", _configure_dingtalk),
    "feishu": ("Feishu", _configure_feishu),
    "imessage": ("iMessage", lambda c: _configure_generic("iMessage", c)),
    "qq": ("QQ", lambda c: _configure_generic("QQ", c)),
    "voice": ("Voice", _configure_voice),
}


def _channel_enabled(ch: dict | None) -> bool:
    if ch is None:
        return False
    if isinstance(ch, dict):
        return bool(ch.get("enabled", False))
    return bool(getattr(ch, "enabled", False))


def configure_channels_interactive(config: dict) -> None:
    """Run channel selection/configuration loop. Mutates config in-place."""
    channels = config.setdefault("channels", {})
    click.echo("\n=== Channel Configuration ===")

    while True:
        channel_choices: list[tuple[str, str]] = []
        for key, (name, _) in _CHANNEL_CONFIGURATORS.items():
            ch = channels.get(key)
            status = "✓" if _channel_enabled(ch) else "✗"
            channel_choices.append((f"{name} [{status}]", key))
        channel_choices.append(("Save and exit", "exit"))

        click.echo()
        choice = prompt_select(
            "Select a channel to configure:",
            options=channel_choices,
        )

        if choice is None or choice == "exit":
            break

        name, configure_func = _CHANNEL_CONFIGURATORS[choice]
        current = channels.get(choice) or {"enabled": False, "bot_prefix": ""}
        if not isinstance(current, dict):
            current = (
                dict(current)
                if hasattr(current, "__iter__")
                else {"enabled": False, "bot_prefix": ""}
            )
        channels[choice] = configure_func(current)

    enabled = [
        name
        for key, (name, _) in _CHANNEL_CONFIGURATORS.items()
        if _channel_enabled(channels.get(key))
    ]
    if enabled:
        click.echo(f"\n✓ Enabled channels: {', '.join(enabled)}")
    else:
        click.echo("\n⚠ Warning: No channels enabled!")


# ── CLI commands ───────────────────────────────────────────────────


@click.group("channels")
def channels_group() -> None:
    """Manage channel configuration."""


@channels_group.command("list")
def list_cmd() -> None:
    """Show current channel configuration."""
    config = load_config()
    channels = config.get("channels", {})

    if not channels:
        click.echo(
            "No channels configured. Run 'researchclaw channels config' to add one.",
        )
        return

    for key, ch in channels.items():
        if not isinstance(ch, dict):
            continue
        name = _ALL_CHANNEL_NAMES.get(key, key)
        status = (
            click.style("enabled", fg="green")
            if ch.get("enabled")
            else click.style("disabled", fg="red")
        )
        click.echo(f"\n{'─' * 40}")
        click.echo(f"  {name}  [{status}]")
        click.echo(f"{'─' * 40}")
        for field_name, value in ch.items():
            if field_name == "enabled":
                continue
            display = (
                _mask(str(value)) if field_name in _SECRET_FIELDS else value
            )
            click.echo(f"  {field_name:20s}: {display}")
    click.echo()


@channels_group.command("config")
def configure_cmd() -> None:
    """Interactively configure channels."""
    config = load_config()
    configure_channels_interactive(config)
    save_config(config)
    click.echo("\n✓ Configuration saved.")


@channels_group.command("install")
@click.argument("key", required=True)
@click.option(
    "--path",
    "from_path",
    type=click.Path(exists=True),
    help="Copy channel from local path",
)
@click.option(
    "--url",
    "from_url",
    type=str,
    help="Download channel module from URL",
)
def install_cmd(key: str, from_path: str | None, from_url: str | None) -> None:
    """Install a channel into the working dir (custom_channels/)."""
    custom_dir = Path(CUSTOM_CHANNELS_DIR)
    custom_dir.mkdir(parents=True, exist_ok=True)

    if not key.isidentifier():
        click.echo(
            f"Key must be a valid Python identifier, got: {key}",
            err=True,
        )
        raise SystemExit(1)

    dest_file = custom_dir / f"{key}.py"

    if from_path:
        import shutil

        src = Path(from_path).resolve()
        if src.is_file():
            shutil.copy2(src, dest_file)
        elif src.is_dir():
            dest_dir = custom_dir / key
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(src, dest_dir)
        click.echo(f"✓ Installed {key} from {src}")
        return

    if from_url:
        import urllib.request

        try:
            with urllib.request.urlopen(from_url) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            click.echo(f"Failed to fetch URL: {e}", err=True)
            raise SystemExit(1) from e
        dest_file.write_text(body, encoding="utf-8")
        click.echo(f"✓ Installed {key}.py from URL")
        return

    if dest_file.exists():
        click.echo(
            f"Channel '{key}' already exists. Use --path or --url to overwrite.",
            err=True,
        )
        raise SystemExit(1)

    dest_file.write_text(CHANNEL_TEMPLATE.format(key=key), encoding="utf-8")
    click.echo(
        f"✓ Created {dest_file}. Edit and add config with 'researchclaw channels config'.",
    )


@channels_group.command("remove")
@click.argument("key", required=True)
def remove_cmd(key: str) -> None:
    """Remove a custom channel from custom_channels/."""
    from ..app.channels.registry import BUILTIN_CHANNEL_KEYS

    if key in BUILTIN_CHANNEL_KEYS:
        click.echo(
            f"'{key}' is a built-in channel. Disable it in config instead.",
            err=True,
        )
        raise SystemExit(1)

    custom_dir = Path(CUSTOM_CHANNELS_DIR)
    dest_file = custom_dir / f"{key}.py"
    dest_dir = custom_dir / key

    if not dest_file.exists() and not dest_dir.exists():
        click.echo(f"Channel '{key}' not found in {custom_dir}.", err=True)
        raise SystemExit(1)

    import shutil

    if dest_file.exists():
        dest_file.unlink()
    else:
        shutil.rmtree(dest_dir)
    click.echo(f"✓ Removed channel '{key}'.")

    # Also remove from config
    config = load_config()
    channels = config.get("channels", {})
    if key in channels:
        del channels[key]
        save_config(config)
        click.echo(f"✓ Removed '{key}' from config.")
