"""MLX backend for Apple-Silicon–native inference.

Install with::

    pip install 'researchclaw[mlx]'
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Generator

from ..schema import LocalModelInfo
from .base import LocalBackend

logger = logging.getLogger(__name__)


def _resolve_model_dir(model_info: LocalModelInfo) -> str:
    """Return the directory that contains the MLX model.

    ``model_info.file_path`` may point to a file *inside* the model dir
    or to the directory itself.
    """
    p = Path(model_info.file_path)
    if p.is_dir():
        return str(p)
    return str(p.parent)


def _normalize_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
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


class MlxBackend(LocalBackend):
    """Run MLX-format models via ``mlx-lm``."""

    def __init__(
        self,
        model_info: LocalModelInfo,
        max_kv_size: int | None = None,
    ) -> None:
        super().__init__(model_info)
        try:
            from mlx_lm import load  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "mlx-lm is required for MLX inference.  "
                "Install with:  pip install 'researchclaw[mlx]'",
            ) from exc

        model_dir = _resolve_model_dir(model_info)
        logger.info("Loading MLX model from %s …", model_dir)
        self._model, self._tokenizer = load(model_dir)
        self._model_dir = model_dir
        self._max_kv_size = max_kv_size

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_prompt(self, messages: list[dict[str, Any]]) -> str:
        """Apply the tokenizer's chat template to *messages*."""
        tok = self._tokenizer
        inner = getattr(tok, "tokenizer", tok)
        if hasattr(inner, "apply_chat_template"):
            return inner.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        # Fallback for tokenizers without a chat template.
        parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"<|{role}|>\n{content}")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Sampler kwargs
    # ------------------------------------------------------------------

    @staticmethod
    def _sampler_kwargs(temperature: float) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"temp": temperature}
        if temperature < 1e-6:
            kwargs["top_p"] = 1.0
        return kwargs

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        from mlx_lm import generate  # type: ignore[import-untyped]

        msgs = _normalize_messages(messages)
        prompt = self._build_prompt(msgs)
        sampler = self._sampler_kwargs(temperature)

        gen_kwargs: dict[str, Any] = {
            "model": self._model,
            "tokenizer": self._tokenizer,
            "prompt": prompt,
            "max_tokens": max_tokens,
            **sampler,
        }
        if self._max_kv_size is not None:
            gen_kwargs["max_kv_size"] = self._max_kv_size

        return generate(**gen_kwargs)

    def chat_completion_stream(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        from mlx_lm import stream_generate  # type: ignore[import-untyped]

        msgs = _normalize_messages(messages)
        prompt = self._build_prompt(msgs)
        sampler = self._sampler_kwargs(temperature)

        gen_kwargs: dict[str, Any] = {
            "model": self._model,
            "tokenizer": self._tokenizer,
            "prompt": prompt,
            "max_tokens": max_tokens,
            **sampler,
        }
        if self._max_kv_size is not None:
            gen_kwargs["max_kv_size"] = self._max_kv_size

        for result in stream_generate(**gen_kwargs):
            token = result.token if hasattr(result, "token") else str(result)
            if token:
                yield token

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            del self._tokenizer
            self._model = None  # type: ignore[assignment]
            self._tokenizer = None  # type: ignore[assignment]
            logger.info("MLX model from %s unloaded.", self._model_dir)

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
