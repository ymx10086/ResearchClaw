"""Multi-agent runner manager with binding-based routing."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from researchclaw.config import load_config
from researchclaw.constant import WORKING_DIR

from .manager import AgentRunnerManager

logger = logging.getLogger(__name__)


@dataclass
class AgentDefinition:
    id: str
    workspace: str
    enabled: bool
    model_config: dict[str, Any]
    autostart: bool = False


@dataclass
class BindingRule:
    agent_id: str
    channel: str = ""
    account_id: str = ""
    user_id: str = ""
    session_id: str = ""
    session_prefix: str = ""


@dataclass
class RouteContext:
    channel: str
    account_id: str
    user_id: str
    session_id: str


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if hasattr(value, "__dict__"):
        return {
            k: v for k, v in value.__dict__.items() if not k.startswith("_")
        }
    return {}


def _get_field(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _normalize_id(value: Any, default: str = "main") -> str:
    text = str(value or "").strip()
    return text or default


def _extract_channel_meta(request: Any) -> dict[str, Any]:
    meta = _get_field(request, "channel_meta", None)
    if isinstance(meta, dict):
        return dict(meta)
    return _as_dict(meta)


def _normalize_workspace(agent_id: str, raw_workspace: Any) -> str:
    if raw_workspace:
        candidate = Path(str(raw_workspace).strip()).expanduser()
        if not candidate.is_absolute():
            candidate = Path(WORKING_DIR) / candidate
    elif agent_id == "main":
        candidate = Path(WORKING_DIR)
    else:
        candidate = Path(WORKING_DIR) / "agents" / agent_id
    return str(candidate.resolve())


def _merge_model_config(
    *,
    global_model: dict[str, Any],
    defaults_model: dict[str, Any],
    item_model: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    merged.update(global_model)
    merged.update(defaults_model)
    merged.update(item_model)
    return {
        k: v
        for k, v in merged.items()
        if v is not None and str(v).strip() != ""
    }


class MultiAgentRunnerManager:
    """Facade that manages isolated per-agent runner managers."""

    def __init__(
        self,
        *,
        config_loader: Callable[..., dict[str, Any]] = load_config,
    ) -> None:
        self._config_loader = config_loader
        self._agents: dict[str, AgentRunnerManager] = {}
        self._definitions: dict[str, AgentDefinition] = {}
        self._bindings: list[BindingRule] = []
        self.default_agent_id = "main"
        self._chat_manager: Any = None
        self._mcp_manager: Any = None
        self._lock = asyncio.Lock()
        self._last_routed_agent_id = "main"

    # ---- compatibility facade for existing code paths ----

    @property
    def is_running(self) -> bool:
        manager = self._agents.get(self.default_agent_id)
        return bool(manager and manager.is_running)

    @property
    def runner(self) -> Any:
        manager = self._agents.get(self.default_agent_id)
        return manager.runner if manager is not None else None

    @property
    def agent(self) -> Any:
        manager = self._agents.get(self.default_agent_id)
        return manager.agent if manager is not None else None

    @property
    def session_manager(self) -> Any:
        manager = self._agents.get(self.default_agent_id)
        return manager.session_manager if manager is not None else None

    # ---- lifecycle ----

    async def start(self) -> None:
        await self.reload_from_config()
        manager = self._agents.get(self.default_agent_id)
        if manager is not None:
            await manager.start()
        for agent_id, definition in self._definitions.items():
            if (
                definition.autostart
                and agent_id != self.default_agent_id
                and definition.enabled
            ):
                await self._agents[agent_id].start()

    async def stop(self) -> None:
        for manager in list(self._agents.values()):
            await manager.stop()

    def set_chat_manager(self, chat_manager: Any) -> None:
        self._chat_manager = chat_manager
        for manager in self._agents.values():
            manager.set_chat_manager(chat_manager)

    def set_mcp_manager(self, mcp_manager: Any) -> None:
        self._mcp_manager = mcp_manager
        for manager in self._agents.values():
            manager.set_mcp_manager(mcp_manager)

    async def refresh_mcp_clients(self, force: bool = False) -> None:
        for manager in self._agents.values():
            await manager.refresh_mcp_clients(force=force)

    async def reload_from_config(self) -> None:
        """Reload agent definitions + bindings from config.json."""
        async with self._lock:
            data = self._config_loader() or {}
            definitions, bindings, default_agent_id = self._parse_config(data)

            # Remove disabled or deleted agents.
            for agent_id in list(self._agents.keys()):
                if (
                    agent_id not in definitions
                    or not definitions[agent_id].enabled
                ):
                    await self._agents[agent_id].stop()
                    self._agents.pop(agent_id, None)

            # Add/update agents.
            for agent_id, definition in definitions.items():
                existing = self._agents.get(agent_id)
                if existing is None:
                    manager = AgentRunnerManager(
                        working_dir=definition.workspace,
                        model_config=definition.model_config,
                        agent_id=agent_id,
                    )
                    if self._chat_manager is not None:
                        manager.set_chat_manager(self._chat_manager)
                    if self._mcp_manager is not None:
                        manager.set_mcp_manager(self._mcp_manager)
                    self._agents[agent_id] = manager
                    continue

                if Path(existing.working_dir) != Path(definition.workspace):
                    await existing.stop()
                    manager = AgentRunnerManager(
                        working_dir=definition.workspace,
                        model_config=definition.model_config,
                        agent_id=agent_id,
                    )
                    if self._chat_manager is not None:
                        manager.set_chat_manager(self._chat_manager)
                    if self._mcp_manager is not None:
                        manager.set_mcp_manager(self._mcp_manager)
                    self._agents[agent_id] = manager
                else:
                    existing._model_config = dict(
                        definition.model_config,
                    )  # noqa: SLF001

            self._definitions = definitions
            self._bindings = bindings
            self.default_agent_id = default_agent_id
            self._last_routed_agent_id = default_agent_id

    # ---- chat facade ----

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        *,
        agent_id: str | None = None,
    ) -> str:
        manager = await self._ensure_manager(agent_id or self.default_agent_id)
        return await manager.chat(message=message, session_id=session_id)

    async def chat_stream(
        self,
        message: str,
        session_id: str | None = None,
        *,
        agent_id: str | None = None,
    ):
        manager = await self._ensure_manager(agent_id or self.default_agent_id)
        async for event in manager.chat_stream(
            message=message,
            session_id=session_id,
        ):
            yield event

    async def stream_query(self, request: Any):
        """Process a channel-origin request with binding-based agent routing."""
        route_ctx = self._route_context_from_request(request)
        preferred = _normalize_id(
            _get_field(request, "agent_id", "") or "",
            "",
        )
        meta = _extract_channel_meta(request)
        if not preferred:
            preferred = _normalize_id(meta.get("agent_id", "") or "", "")

        agent_id = self._resolve_agent_id(
            route_ctx,
            preferred_agent_id=preferred,
        )
        manager = await self._ensure_manager(agent_id)
        self._last_routed_agent_id = agent_id

        # Stamp resolved agent id for observability.
        if isinstance(request, dict):
            request["agent_id"] = agent_id
            request.setdefault("channel_meta", {})
            if isinstance(request["channel_meta"], dict):
                request["channel_meta"]["agent_id"] = agent_id
        else:
            try:
                setattr(request, "agent_id", agent_id)
            except Exception:
                pass
            meta_obj = _get_field(request, "channel_meta", None)
            if meta_obj is None:
                try:
                    setattr(request, "channel_meta", {"agent_id": agent_id})
                except Exception:
                    pass
            elif isinstance(meta_obj, dict):
                meta_obj["agent_id"] = agent_id

        async for event in manager.stream_query(request):
            if isinstance(event, dict):
                event.setdefault("agent_id", agent_id)
            else:
                try:
                    setattr(event, "agent_id", agent_id)
                except Exception:
                    pass
            yield event

    async def apply_provider(
        self,
        model_config: dict[str, Any],
        *,
        agent_id: str | None = None,
    ) -> None:
        manager = await self._ensure_manager(agent_id or self.default_agent_id)
        await manager.apply_provider(model_config)

    # ---- session facade ----

    def list_agents(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for agent_id, definition in sorted(self._definitions.items()):
            manager = self._agents.get(agent_id)
            running = bool(manager and manager.is_running)
            session_count = 0
            usage: dict[str, Any] = {}
            if manager is not None:
                try:
                    session_count = len(
                        manager.session_manager.list_sessions(),
                    )
                except Exception:
                    session_count = 0
                if hasattr(manager, "get_usage_stats"):
                    try:
                        usage = manager.get_usage_stats()
                    except Exception:
                        usage = {}
            rows.append(
                {
                    "id": agent_id,
                    "enabled": definition.enabled,
                    "workspace": definition.workspace,
                    "running": running,
                    "session_count": session_count,
                    "default": agent_id == self.default_agent_id,
                    "usage": usage,
                },
            )
        return rows

    def list_sessions(
        self,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if agent_id:
            manager = self._agents.get(agent_id)
            if manager is None:
                return []
            for row in manager.session_manager.list_sessions():
                item = dict(row)
                item["agent_id"] = agent_id
                out.append(item)
            return out

        for aid, manager in self._agents.items():
            for row in manager.session_manager.list_sessions():
                item = dict(row)
                item["agent_id"] = aid
                out.append(item)

        out.sort(key=lambda x: float(x.get("updated_at") or 0), reverse=True)
        return out

    def get_session(self, *, agent_id: str, session_id: str) -> Any:
        manager = self._agents.get(agent_id)
        if manager is None:
            return None
        return manager.session_manager.get_session(session_id)

    def get_session_manager(self, agent_id: str) -> Any:
        manager = self._agents.get(agent_id)
        if manager is None:
            return None
        return manager.session_manager

    def delete_session(self, *, agent_id: str, session_id: str) -> bool:
        manager = self._agents.get(agent_id)
        if manager is None:
            return False
        existing = manager.session_manager.get_session(session_id)
        if not existing:
            return False
        manager.session_manager.delete_session(session_id)
        return True

    def list_usage_stats(self, agent_id: str | None = None) -> dict[str, Any]:
        if agent_id:
            manager = self._agents.get(agent_id)
            if manager is None or not hasattr(manager, "get_usage_stats"):
                return {
                    "agent_id": agent_id,
                    "requests": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "fallbacks": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "providers": [],
                }
            return manager.get_usage_stats()

        totals = {
            "requests": 0,
            "succeeded": 0,
            "failed": 0,
            "fallbacks": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        providers: dict[str, dict[str, Any]] = {}
        by_agent: list[dict[str, Any]] = []

        for aid, manager in sorted(self._agents.items()):
            if not hasattr(manager, "get_usage_stats"):
                continue
            item = manager.get_usage_stats()
            by_agent.append(item)
            for key in totals:
                totals[key] += int(item.get(key, 0) or 0)
            for row in item.get("providers", []) or []:
                provider = str(row.get("provider", "") or "")
                model_name = str(row.get("model_name", "") or "")
                k = f"{provider}::{model_name}"
                agg = providers.setdefault(
                    k,
                    {
                        "provider": provider,
                        "model_name": model_name,
                        "requests": 0,
                        "succeeded": 0,
                        "failed": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                    },
                )
                agg["requests"] += int(row.get("requests", 0) or 0)
                agg["succeeded"] += int(row.get("succeeded", 0) or 0)
                agg["failed"] += int(row.get("failed", 0) or 0)
                agg["input_tokens"] += int(row.get("input_tokens", 0) or 0)
                agg["output_tokens"] += int(row.get("output_tokens", 0) or 0)

        provider_rows = list(providers.values())
        provider_rows.sort(
            key=lambda x: (
                int(x.get("requests", 0)),
                str(x.get("model_name", "")),
            ),
            reverse=True,
        )
        return {
            **totals,
            "agents": by_agent,
            "providers": provider_rows,
        }

    # ---- internals ----

    async def _ensure_manager(self, agent_id: str) -> AgentRunnerManager:
        normalized = _normalize_id(agent_id or self.default_agent_id)
        manager = self._agents.get(normalized)
        if manager is None:
            # Config might have changed on disk; one reload attempt.
            await self.reload_from_config()
            manager = self._agents.get(normalized)
        if manager is None:
            manager = self._agents.get(self.default_agent_id)
            normalized = self.default_agent_id
        if manager is None:
            raise RuntimeError("No active agent manager configured")
        if not manager.is_running:
            await manager.start()
        self._last_routed_agent_id = normalized
        return manager

    def _route_context_from_request(self, request: Any) -> RouteContext:
        channel = str(_get_field(request, "channel", "") or "").strip().lower()
        user_id = str(_get_field(request, "user_id", "") or "").strip()
        session_id = str(_get_field(request, "session_id", "") or "").strip()

        meta = _extract_channel_meta(request)
        account_id = str(
            meta.get("account_id")
            or meta.get("accountId")
            or _get_field(request, "account_id", "")
            or "",
        ).strip()

        if ":" in channel:
            base, maybe_account = channel.split(":", 1)
            if base and not account_id:
                account_id = maybe_account.strip()
            channel = base.strip().lower()

        return RouteContext(
            channel=channel or "console",
            account_id=account_id,
            user_id=user_id or "main",
            session_id=session_id or "main",
        )

    def _resolve_agent_id(
        self,
        ctx: RouteContext,
        *,
        preferred_agent_id: str = "",
    ) -> str:
        preferred = _normalize_id(preferred_agent_id, "")
        if preferred and preferred in self._agents:
            return preferred

        for rule in self._bindings:
            if rule.channel and rule.channel != ctx.channel:
                continue
            if rule.account_id and rule.account_id != ctx.account_id:
                continue
            if rule.user_id and rule.user_id != ctx.user_id:
                continue
            if rule.session_id and rule.session_id != ctx.session_id:
                continue
            if rule.session_prefix and not ctx.session_id.startswith(
                rule.session_prefix,
            ):
                continue
            if rule.agent_id in self._agents:
                return rule.agent_id

        if self.default_agent_id in self._agents:
            return self.default_agent_id
        if self._agents:
            return next(iter(self._agents.keys()))
        return "main"

    def _parse_config(
        self,
        data: dict[str, Any],
    ) -> tuple[dict[str, AgentDefinition], list[BindingRule], str]:
        agents_cfg = data.get("agents")
        if not isinstance(agents_cfg, dict):
            agents_cfg = {}
        defaults = agents_cfg.get("defaults")
        if not isinstance(defaults, dict):
            defaults = {}

        global_model = {
            "provider": data.get("provider"),
            "model_name": data.get("model_name"),
            "api_key": data.get("api_key"),
            "base_url": data.get("base_url"),
        }
        defaults_model = defaults.get("model")
        defaults_model = (
            defaults_model if isinstance(defaults_model, dict) else {}
        )

        raw_list = agents_cfg.get("list")
        raw_list = raw_list if isinstance(raw_list, list) else []
        if not raw_list:
            raw_list = [{"id": "main"}]

        definitions: dict[str, AgentDefinition] = {}
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue
            agent_id = _normalize_id(raw.get("id") or raw.get("agent_id"), "")
            if not agent_id:
                continue
            enabled = bool(raw.get("enabled", True))
            workspace = _normalize_workspace(agent_id, raw.get("workspace"))
            Path(workspace).mkdir(parents=True, exist_ok=True)
            item_model = raw.get("model")
            item_model = item_model if isinstance(item_model, dict) else {}
            model_config = _merge_model_config(
                global_model=global_model,
                defaults_model=defaults_model,
                item_model=item_model,
            )
            model_config.setdefault("working_dir", workspace)

            definitions[agent_id] = AgentDefinition(
                id=agent_id,
                workspace=workspace,
                enabled=enabled,
                model_config=model_config,
                autostart=bool(raw.get("autostart", False)),
            )

        if not definitions:
            workspace = _normalize_workspace("main", None)
            Path(workspace).mkdir(parents=True, exist_ok=True)
            definitions["main"] = AgentDefinition(
                id="main",
                workspace=workspace,
                enabled=True,
                model_config={"working_dir": workspace},
            )

        default_agent_id = _normalize_id(
            defaults.get("agent_id")
            or defaults.get("default_agent_id")
            or defaults.get("id"),
            "",
        )
        if not default_agent_id or default_agent_id not in definitions:
            default_agent_id = (
                "main"
                if "main" in definitions
                else next(iter(definitions.keys()))
            )

        raw_bindings = data.get("bindings")
        if not isinstance(raw_bindings, list):
            raw_bindings = agents_cfg.get("bindings")
            if not isinstance(raw_bindings, list):
                raw_bindings = []

        bindings: list[BindingRule] = []
        for item in raw_bindings:
            if not isinstance(item, dict):
                continue
            agent_id = _normalize_id(
                item.get("agent_id") or item.get("agentId"),
                "",
            )
            if not agent_id or agent_id not in definitions:
                continue
            match = item.get("match")
            match = match if isinstance(match, dict) else {}
            bindings.append(
                BindingRule(
                    agent_id=agent_id,
                    channel=str(match.get("channel", "") or "")
                    .strip()
                    .lower(),
                    account_id=str(
                        match.get("account_id")
                        or match.get("accountId")
                        or "",
                    ).strip(),
                    user_id=str(
                        match.get("user_id") or match.get("userId") or "",
                    ).strip(),
                    session_id=str(
                        match.get("session_id")
                        or match.get("sessionId")
                        or "",
                    ).strip(),
                    session_prefix=str(
                        match.get("session_prefix")
                        or match.get("sessionPrefix")
                        or "",
                    ).strip(),
                ),
            )

        return definitions, bindings, default_agent_id
