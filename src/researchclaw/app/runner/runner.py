"""Agent runner – wraps ScholarAgent for async web usage."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


class AgentRunner:
    """Wraps a ScholarAgent instance for use in the web server context.

    Handles:
    - Agent initialisation with model config
    - Async chat dispatch (runs blocking agent reply in executor)
    - Session state tracking
    """

    def __init__(self):
        self.agent = None
        self._lock = asyncio.Lock()
        self._is_running = False
        self._mcp_manager = None
        self._last_model_config: dict[str, Any] = {}
        self._last_mcp_fingerprint: tuple[Any, ...] | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running and self.agent is not None

    async def start(self, model_config: dict[str, Any] | None = None):
        """Initialise the ScholarAgent."""
        async with self._lock:
            if self.agent is not None:
                logger.info("Agent already running, skipping start")
                return

            try:
                config = model_config or {}
                from researchclaw.agents import ScholarAgent

                llm_cfg = {
                    "model_type": config.get("provider", "openai_chat"),
                    "model_name": config.get("model_name", "gpt-4o"),
                    "api_key": config.get("api_key", ""),
                }
                if config.get("base_url"):
                    llm_cfg["api_url"] = config.get("base_url")

                self.agent = ScholarAgent(
                    llm_cfg=llm_cfg,
                    working_dir=config.get("working_dir") or WORKING_DIR,
                )
                self._last_model_config = dict(config)
                await self._attach_mcp_clients_if_any()
                self._is_running = True
                logger.info("ScholarAgent started successfully")
            except Exception:
                logger.exception("Failed to start ScholarAgent")
                raise

    def set_mcp_manager(self, mcp_manager: Any) -> None:
        """Bind MCP manager for tool client discovery."""
        self._mcp_manager = mcp_manager
        self._last_mcp_fingerprint = None

    @staticmethod
    def _build_mcp_fingerprint(clients: list[Any]) -> tuple[Any, ...]:
        items: list[Any] = []
        for client in clients:
            info = getattr(client, "_researchclaw_rebuild_info", None)
            if info is None:
                info = repr(client)
            items.append(str(info))
        return tuple(sorted(items))

    async def _attach_mcp_clients_if_any(self, force: bool = False) -> None:
        if self.agent is None or self._mcp_manager is None:
            return
        try:
            clients = await self._mcp_manager.get_clients()
            if not clients:
                return

            fingerprint = self._build_mcp_fingerprint(clients)
            if not force and fingerprint == self._last_mcp_fingerprint:
                return

            self.agent.register_mcp_clients(clients)
            self._last_mcp_fingerprint = fingerprint
            logger.info("Attached %d MCP client(s) to agent", len(clients))
        except Exception:
            logger.exception("Failed to attach MCP clients to agent")

    async def refresh_mcp_clients(self, force: bool = False) -> None:
        """Attach latest MCP clients to current agent instance."""
        await self._attach_mcp_clients_if_any(force=force)

    async def stop(self):
        """Stop the agent."""
        async with self._lock:
            self.agent = None
            self._is_running = False
            logger.info("ScholarAgent stopped")

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
    ) -> str:
        """Send a message to the agent and get a response.

        The agent's ``reply`` method is blocking, so we run it in an executor.
        """
        if not self.agent:
            raise RuntimeError("Agent is not running")

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.agent.reply(message, session_id=session_id),
        )

        if hasattr(response, "content"):
            return response.content
        return str(response)

    async def chat_stream(
        self,
        message: str,
        session_id: str | None = None,
    ):
        """Stream a response from the agent, yielding SSE event dicts.

        Runs the blocking generator in an executor via a queue.
        """
        if not self.agent:
            raise RuntimeError("Agent is not running")

        import queue
        import threading

        q: queue.Queue = queue.Queue()

        def _run():
            try:
                for event in self.agent.reply_stream(
                    message,
                    session_id=session_id,
                ):
                    q.put(event)
            except Exception as e:
                q.put({"type": "error", "content": str(e)})
            finally:
                q.put(None)  # sentinel

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        while True:
            # Check queue in a non-blocking way to keep the async loop alive
            try:
                event = await asyncio.get_event_loop().run_in_executor(
                    None,
                    q.get,
                    True,
                    60.0,
                )
            except Exception:
                break
            if event is None:
                break
            yield event

    async def restart(self, model_config: dict[str, Any] | None = None):
        """Restart the agent with a new configuration."""
        await self.stop()
        await self.start(model_config)
