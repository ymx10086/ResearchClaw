"""Token counting utilities for managing context windows.

This module provides token counting functionality for estimating
message token usage. Supports tiktoken (OpenAI) and HuggingFace
tokenizers with automatic fallback.

Enhanced from CoPaw with multi-tokenizer support and async API.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_token_counter = None


def _get_token_counter() -> Any:
    """Get or initialize the global token counter instance.

    Tries tiktoken first (OpenAI models), then HuggingFace tokenizer,
    then falls back to character-based estimation.

    Returns:
        A tokenizer object with an ``encode`` method, or None.
    """
    global _token_counter
    if _token_counter is not None:
        return _token_counter

    # Try tiktoken first (works well for OpenAI models)
    try:
        import tiktoken

        _token_counter = tiktoken.get_encoding("cl100k_base")
        logger.info("Token counter initialized with tiktoken (cl100k_base)")
        return _token_counter
    except ImportError:
        logger.debug("tiktoken not available, trying HuggingFace tokenizer")

    # Try HuggingFace tokenizer as fallback
    try:
        from pathlib import Path

        local_tokenizer_path = (
            Path(__file__).parent.parent.parent / "tokenizer"
        )

        if (
            local_tokenizer_path.exists()
            and (local_tokenizer_path / "tokenizer.json").exists()
        ):
            tokenizer_path = str(local_tokenizer_path)
            logger.info(f"Using local tokenizer from {tokenizer_path}")
        else:
            tokenizer_path = "Qwen/Qwen2.5-7B-Instruct"
            logger.info(
                "Local tokenizer not found, trying HuggingFace download",
            )

        from agentscope.token import HuggingFaceTokenCounter

        counter = HuggingFaceTokenCounter(
            pretrained_model_name_or_path=tokenizer_path,
            use_mirror=True,
            use_fast=True,
            trust_remote_code=True,
        )
        _token_counter = counter.tokenizer
        logger.debug("Token counter initialized with HuggingFace tokenizer")
        return _token_counter
    except Exception as e:
        logger.debug("HuggingFace tokenizer init failed: %s", e)

    logger.warning(
        "No tokenizer available. Token counts will use character estimation.",
    )
    return None


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text string.

    Uses tiktoken if available, otherwise falls back to a character-based
    estimate.

    Parameters
    ----------
    text:
        Text to estimate token count for.

    Returns
    -------
    int
        Estimated token count.
    """
    counter = _get_token_counter()
    if counter is not None:
        try:
            return len(counter.encode(text))
        except Exception:
            pass
    # Rough estimate: ~3 characters per token (blend of English and CJK)
    return len(text) // 3


def _extract_text_from_messages(messages: list[dict]) -> str:
    """Extract text content from messages and concatenate into a string.

    Handles various message formats:
    - Simple string content: {"role": "user", "content": "hello"}
    - List content with text blocks:
      {"role": "user", "content": [{"type": "text", "text": "hello"}]}

    Args:
        messages: List of message dictionaries in chat format.

    Returns:
        str: Concatenated text content from all messages.
    """
    parts: list[str] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text") or block.get("content", "")
                    if text:
                        parts.append(str(text))
                elif isinstance(block, str):
                    parts.append(block)
    return "\n".join(parts)


async def count_message_tokens(
    messages: list[dict],
) -> int:
    """Count tokens in messages using the tokenizer.

    Extracts text content from messages and uses the tokenizer to
    count tokens.

    Args:
        messages: List of message dictionaries in chat format.

    Returns:
        int: The estimated number of tokens in the messages.
    """
    text = _extract_text_from_messages(messages)
    return estimate_tokens(text)


async def safe_count_message_tokens(
    messages: list[dict],
) -> int:
    """Safely count tokens in messages with fallback estimation.

    This is a wrapper around count_message_tokens that catches exceptions
    and falls back to a character-based estimation if the tokenizer fails.

    Args:
        messages: List of message dictionaries in chat format.

    Returns:
        int: The estimated number of tokens in the messages.
    """
    try:
        return await count_message_tokens(messages)
    except Exception as e:
        text = _extract_text_from_messages(messages)
        estimated_tokens = len(text) // 4
        logger.warning(
            "Failed to count tokens: %s, using estimated_tokens=%d",
            e,
            estimated_tokens,
        )
        return estimated_tokens


def safe_count_str_tokens(text: str) -> int:
    """Safely count tokens in a string with fallback estimation.

    Uses the tokenizer to count tokens in the given text. If the tokenizer
    fails, falls back to a character-based estimation (len // 4).

    Args:
        text: The string to count tokens for.

    Returns:
        int: The estimated number of tokens in the string.
    """
    try:
        return estimate_tokens(text)
    except Exception as e:
        estimated_tokens = len(text) // 4
        logger.warning(
            "Failed to count string tokens: %s, using estimated_tokens=%d",
            e,
            estimated_tokens,
        )
        return estimated_tokens
