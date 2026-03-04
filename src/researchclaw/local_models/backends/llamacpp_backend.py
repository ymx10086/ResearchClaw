"""llama-cpp-python backend for GGUF models.

Install with::

    pip install 'researchclaw[llamacpp]'
"""

from __future__ import annotations

import logging
from typing import Any, Generator

from ..schema import LocalModelInfo
from .base import LocalBackend

logger = logging.getLogger(__name__)


def _normalize_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ensure ``content`` is always a plain string.

    llama-cpp-python does not accept the ``list[dict]`` content format
    used by multi-modal models.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    parts.append(part.get("text", ""))
                else:
                    parts.append(str(part))
            content = "\n".join(parts)
        out.append({**msg, "content": content})
    return out


class LlamaCppBackend(LocalBackend):
    """Run GGUF models via ``llama-cpp-python``."""

    def __init__(
        self,
        model_info: LocalModelInfo,
        n_ctx: int = 32768,
        n_gpu_layers: int = -1,
    ) -> None:
        super().__init__(model_info)
        try:
            from llama_cpp import Llama  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "llama-cpp-python is required for GGUF inference.  "
                "Install with:  pip install 'researchclaw[llamacpp]'",
            ) from exc

        self._llm = Llama(
            model_path=model_info.file_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        msgs = _normalize_messages(messages)

        create_kwargs: dict[str, Any] = {
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if kwargs.get("response_format") == {"type": "json_object"}:
            create_kwargs["response_format"] = {"type": "json_object"}

        resp = self._llm.create_chat_completion(**create_kwargs)
        return resp["choices"][0]["message"]["content"]  # type: ignore[index]

    def chat_completion_stream(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        msgs = _normalize_messages(messages)

        create_kwargs: dict[str, Any] = {
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        for chunk in self._llm.create_chat_completion(**create_kwargs):
            delta = chunk["choices"][0].get("delta", {})  # type: ignore[index]
            token = delta.get("content")
            if token:
                yield token

    def unload(self) -> None:
        if self._llm is not None:
            del self._llm
            self._llm = None  # type: ignore[assignment]
            logger.info("LlamaCpp model unloaded.")

    @property
    def is_loaded(self) -> bool:
        return self._llm is not None
