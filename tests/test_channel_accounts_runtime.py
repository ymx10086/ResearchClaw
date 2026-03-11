from __future__ import annotations

from types import SimpleNamespace

from researchclaw.app.channels.base import BaseChannel
from researchclaw.app.channels.manager import ChannelManager


class _FakeChannel(BaseChannel):
    channel = "fake"

    @classmethod
    def from_config(cls, process, config, on_reply_sent=None, show_tool_details=True, **kwargs):
        inst = cls(
            process,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )
        inst.enabled = getattr(config, "enabled", True)
        inst.bot_prefix = getattr(config, "bot_prefix", "")
        return inst

    @classmethod
    def from_env(cls, process, on_reply_sent=None):
        return cls(process, on_reply_sent=on_reply_sent)

    async def start(self):
        return None

    async def stop(self):
        return None

    async def send(self, to_handle: str, text: str, meta=None):
        return None

    def build_agent_request_from_native(self, native_payload):
        return native_payload


def test_channel_manager_builds_account_aliases(monkeypatch):
    monkeypatch.setattr(
        "researchclaw.app.channels.registry.get_channel_registry",
        lambda: {"fake": _FakeChannel},
    )

    cfg = SimpleNamespace(
        channels=SimpleNamespace(
            available=["fake"],
            fake=SimpleNamespace(enabled=True, bot_prefix="[BOT] "),
        ),
        channel_accounts={
            "fake": {
                "lab": {"enabled": True, "bot_prefix": "[LAB] "},
                "disabled": {"enabled": False},
            },
        },
    )

    manager = ChannelManager.from_config(
        process=lambda req: req,
        config=cfg,
    )
    names = [ch.channel for ch in manager.channels]

    assert "fake" in names
    assert "fake:lab" in names
    assert "fake:disabled" not in names
