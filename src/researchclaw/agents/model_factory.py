"""Model factory – unified creation of LLM model instances and formatters.

Mirrors the CoPaw pattern: a single ``create_model_and_formatter()`` entry
point that returns ``(model, formatter)`` ready for the ScholarAgent.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..constant import DEFAULT_MODEL_NAME

logger = logging.getLogger(__name__)


def create_model_and_formatter(
    llm_cfg: Optional[dict[str, Any]] = None,
) -> tuple[Any, Any]:
    """Create an LLM model wrapper and its formatter.

    Parameters
    ----------
    llm_cfg:
        Optional model configuration dict. If *None*, the active LLM config
        is loaded from ``config.json``.

    Returns
    -------
    tuple[model, formatter]
        Ready-to-use model and formatter instances.
    """
    if llm_cfg is None:
        llm_cfg = _get_active_llm_config()

    model_type = llm_cfg.get("model_type", "openai_chat")

    # Local model shortcut
    if model_type in ("local", "llamacpp", "mlx", "ollama"):
        return _create_local_model(llm_cfg)

    return _create_remote_model(llm_cfg)


def _get_active_llm_config() -> dict[str, Any]:
    """Load the currently active LLM configuration."""
    try:
        from ..config.config import load_config

        config = load_config()
        providers = config.get("providers", {})
        active = providers.get("active")
        if active and active in providers.get("configs", {}):
            return providers["configs"][active]
    except Exception:
        logger.debug("Could not load active LLM config, using defaults")

    return {
        "model_type": "openai_chat",
        "model_name": DEFAULT_MODEL_NAME,
        "api_key": "",
    }


def _create_remote_model(llm_cfg: dict[str, Any]) -> tuple[Any, Any]:
    """Instantiate a remote (API-based) model and formatter."""
    try:
        from agentscope.models import OpenAIChatWrapper

        model_name = llm_cfg.get("model_name", DEFAULT_MODEL_NAME)
        api_key = llm_cfg.get("api_key", "")
        api_url = llm_cfg.get("api_url", None)

        config = {
            "config_name": f"researchclaw_{model_name}",
            "model_type": "openai_chat",
            "model_name": model_name,
            "api_key": api_key,
        }
        if api_url:
            config["client_args"] = {"base_url": api_url}

        model = OpenAIChatWrapper(**config)
        formatter = _create_formatter(model)
        return model, formatter

    except ImportError:
        logger.error(
            "agentscope is required for model creation. "
            "Install it with: pip install agentscope",
        )
        raise


def _create_local_model(llm_cfg: dict[str, Any]) -> tuple[Any, Any]:
    """Instantiate a local model (Ollama, llama.cpp, etc.)."""
    model_type = llm_cfg.get("model_type", "ollama")

    if model_type == "ollama":
        try:
            from agentscope.models import OllamaChatWrapper

            config = {
                "config_name": f"researchclaw_ollama_{llm_cfg.get('model_name', 'llama3')}",
                "model_type": "ollama_chat",
                "model_name": llm_cfg.get("model_name", "llama3"),
            }
            if "api_url" in llm_cfg:
                config["client_args"] = {"base_url": llm_cfg["api_url"]}

            model = OllamaChatWrapper(**config)
            formatter = _create_formatter(model)
            return model, formatter

        except ImportError:
            logger.error(
                "Ollama support requires agentscope with ollama extras",
            )
            raise

    # Fallback: treat as OpenAI-compatible
    return _create_remote_model(llm_cfg)


def _create_formatter(model: Any) -> Any:
    """Create a message formatter that supports FileBlock in tool results.

    Wraps the model's default formatter to properly handle file blocks
    returned by research tools (PDFs, figures, etc.).
    """
    try:
        from agentscope.formatters import OpenAIFormatter

        class ResearchFormatter(OpenAIFormatter):
            """Extended formatter with research file block support."""

            def convert_tool_result_to_string(self, result: Any) -> str:
                """Handle FileBlock and PaperInfo results gracefully."""
                if isinstance(result, dict):
                    block_type = result.get("type")
                    if block_type == "file":
                        filename = result.get("filename", "file")
                        return f"[File: {filename}]"
                    if "title" in result and "authors" in result:
                        # PaperInfo-like dict
                        title = result["title"]
                        authors = ", ".join(result.get("authors", [])[:3])
                        year = result.get("year", "")
                        return f"📄 {title} ({authors}, {year})"

                if isinstance(result, list):
                    parts = [
                        self.convert_tool_result_to_string(r) for r in result
                    ]
                    return "\n".join(parts)

                return str(result)

        return ResearchFormatter()

    except ImportError:
        logger.debug(
            "Using default formatter (agentscope formatters not available)",
        )
        return None
