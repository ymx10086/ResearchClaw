from __future__ import annotations

import asyncio
from types import SimpleNamespace

from researchclaw.app.automation.trigger_store import AutomationRunStore
from researchclaw.app.routers import automation as automation_router


def _make_req(channel_names: list[str]):
    mgr = SimpleNamespace(
        list_channels=lambda: [{"name": name} for name in channel_names],
    )
    state = SimpleNamespace(channel_manager=mgr)
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def test_dedupe_dispatches_normalizes_values() -> None:
    out = automation_router._dedupe_dispatches(
        [
            {"channel": "Telegram", "user_id": "u1", "session_id": "s1"},
            {"channel": " telegram ", "user_id": "u1", "session_id": "s1"},
            {"channel": "discord", "user_id": "", "session_id": ""},
        ],
    )
    assert out == [
        {"channel": "telegram", "user_id": "u1", "session_id": "s1"},
        {"channel": "discord", "user_id": "main", "session_id": "main"},
    ]


def test_expand_dispatches_supports_fanout_star() -> None:
    req = _make_req(["console", "telegram", "discord"])
    payload = automation_router.AgentTriggerRequest(
        message="ping",
        deliver=True,
        fanout_channels=["*"],
        user_id="owner",
        run_async=False,
    )
    out = automation_router._expand_dispatches(
        payload=payload,
        req=req,
        default_session_id="automation:1",
    )
    assert {item["channel"] for item in out} == {
        "console",
        "telegram",
        "discord",
    }
    assert {item["user_id"] for item in out} == {"owner"}
    assert {item["session_id"] for item in out} == {"automation:1"}


def test_expand_dispatches_falls_back_to_last_dispatch(monkeypatch) -> None:
    req = _make_req(["console"])
    payload = automation_router.AgentTriggerRequest(
        message="ping",
        deliver=True,
        run_async=False,
    )
    monkeypatch.setattr(
        automation_router,
        "load_config",
        lambda: {
            "last_dispatch": {
                "channel": "telegram",
                "user_id": "alice",
                "session_id": "tg:1001",
            },
        },
    )
    out = automation_router._expand_dispatches(
        payload=payload,
        req=req,
        default_session_id="automation:2",
    )
    assert out == [
        {"channel": "telegram", "user_id": "alice", "session_id": "tg:1001"},
    ]


def test_automation_run_store_lifecycle() -> None:
    async def _run():
        store = AutomationRunStore(max_runs=50)
        created = await store.create(
            run_id="r1",
            message="hello",
            session_id="automation:r1",
            deliver=True,
            dispatches=[
                {
                    "channel": "console",
                    "user_id": "main",
                    "session_id": "main",
                },
            ],
        )
        assert created["status"] == "queued"

        running = await store.mark_running("r1")
        assert running is not None
        assert running["status"] == "running"

        done = await store.mark_success(
            "r1",
            response="ok",
            delivery_results=[{"ok": True, "channel": "console"}],
        )
        assert done is not None
        assert done["status"] == "succeeded"

        stats = await store.stats()
        assert stats["total"] == 1
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0

        listed = await store.list(limit=10)
        assert len(listed) == 1
        assert listed[0]["id"] == "r1"

    asyncio.run(_run())


def test_render_template_and_mapping_message() -> None:
    body = {
        "event": {
            "title": "new paper",
            "author": {"name": "alice"},
        },
        "message": "fallback text",
    }
    rendered = automation_router._render_template(
        "Paper: {{event.title}} by {{event.author.name}}",
        body,
    )
    assert rendered == "Paper: new paper by alice"

    mapped = automation_router._extract_message_from_mapping(
        {"message_template": "From {{event.author.name}}"},
        body,
    )
    assert mapped == "From alice"

    from_field = automation_router._extract_message_from_mapping(
        {"message_field": "event.title"},
        body,
    )
    assert from_field == "new paper"


def test_wake_to_agent_payload_conversion() -> None:
    wake = automation_router.WakeTriggerRequest(
        text="cron heartbeat",
        mode="now",
        agent_id="research",
        run_async=False,
    )
    payload = automation_router._wake_to_agent_trigger(wake)
    assert payload.agent_id == "research"
    assert payload.run_async is False
    assert payload.message.startswith("[Wake trigger:now]")
