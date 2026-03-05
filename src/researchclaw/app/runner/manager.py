"""AgentRunnerManager – top-level manager for the agent runner lifecycle."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from researchclaw.app.runner.runner import AgentRunner
from researchclaw.app.runner.session import SessionManager
from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


class AgentRunnerManager:
    """Coordinates agent runner and session management.

    Used in the FastAPI lifespan to start/stop the agent, and provides
    a unified interface for chat operations.
    """

    def __init__(self):
        self.runner = AgentRunner()
        self.session_manager = SessionManager()
        self._model_config: dict[str, Any] = {}

    @property
    def is_running(self) -> bool:
        return self.runner.is_running

    @property
    def agent(self):
        return self.runner.agent

    async def start(self):
        """Start the agent runner with persisted config."""
        self._model_config = self._load_model_config()
        if self._model_config.get("model_name") or self._model_config.get(
            "api_key",
        ):
            try:
                await self.runner.start(self._model_config)
            except Exception:
                logger.warning(
                    "Failed to auto-start agent. "
                    "Configure model via CLI or API and restart.",
                )
        else:
            logger.info(
                "No model configured. Use 'researchclaw init' or the "
                "API to set up a model before chatting.",
            )

    async def stop(self):
        """Stop the agent runner."""
        await self.runner.stop()

    async def chat(self, message: str, session_id: str | None = None) -> str:
        """Send a chat message, creating a session if needed."""
        if not self.runner.is_running:
            # Try to start with current config
            await self.start()
            if not self.runner.is_running:
                return (
                    "Scholar is not ready. Please configure your LLM provider first.\n"
                    "Run `researchclaw init` or set up via Settings."
                )

        session = None
        if session_id:
            session = self.session_manager.get_session(session_id)
        if not session:
            session = self.session_manager.create_session()

        session.add_message("user", message)
        response = await self.runner.chat(message, session.session_id)
        session.add_message("assistant", response)
        self.session_manager._save_session(session)

        return response

    async def apply_provider(self, model_config: dict[str, Any]) -> None:
        """Hot-reload the agent with a new provider config."""
        logger.info(
            "Applying new provider config: %s / %s",
            model_config.get("provider"),
            model_config.get("model_name"),
        )
        await self.runner.restart(model_config)
        self._model_config = model_config
        logger.info("Agent restarted with new provider config")

    def _load_model_config(self) -> dict[str, Any]:
        """Load model config from working directory."""
        config_path = Path(WORKING_DIR) / "config.json"
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
