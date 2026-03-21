from __future__ import annotations

from fastapi import FastAPI

from researchclaw.app.gateway.auth import extract_header_token
from researchclaw.app.gateway.dispatch import coerce_dispatch_target
from researchclaw.app.gateway.health import runtime_component_flags
from researchclaw.app.gateway.ingress import default_session_id
from researchclaw.app.gateway.runtime import (
    GatewayRuntime,
    build_channel_runtime_config,
)


def test_build_channel_runtime_config_injects_console_defaults() -> None:
    runtime_config = build_channel_runtime_config(
        {
            "telegram": {"enabled": True},
            "show_tool_details": False,
        },
    )

    assert runtime_config.channels.console.enabled is True
    assert runtime_config.channels.console.bot_prefix == "[BOT] "
    assert set(runtime_config.channels.available) == {"console", "telegram"}
    assert runtime_config.show_tool_details is False


def test_gateway_runtime_snapshot_and_health_flags() -> None:
    app = FastAPI()
    runtime = GatewayRuntime(app)
    runtime.bind("runner", object())
    runtime.bind("channel_manager", object())
    runtime.bind("started_at", 123.0)

    snapshot = runtime.snapshot()

    assert snapshot.runner is not None
    assert snapshot.channel_manager is not None
    assert snapshot.started_at == 123.0
    assert runtime_component_flags(snapshot) == {
        "runner": True,
        "chat_manager": False,
        "channel_manager": True,
        "mcp_manager": False,
        "mcp_watcher": False,
        "cron_manager": False,
        "config_watcher": False,
        "automation_store": False,
        "research_service": False,
        "research_runtime": False,
    }


def test_default_session_id_and_dispatch_target_normalization() -> None:
    session_id = default_session_id(prefix="automation")
    target = coerce_dispatch_target(
        channel=" Console ",
        user_id="",
        session_id="",
    )

    assert session_id.startswith("automation:")
    assert target is not None
    assert target.channel == "console"
    assert target.user_id == "main"
    assert target.session_id == "main"


def test_extract_header_token_prefers_bearer_then_custom_headers() -> None:
    assert (
        extract_header_token(
            {"authorization": "Bearer abc"},
            "x-researchclaw-token",
        )
        == "abc"
    )
    assert (
        extract_header_token(
            {"x-researchclaw-token": "xyz"},
            "x-researchclaw-token",
        )
        == "xyz"
    )
