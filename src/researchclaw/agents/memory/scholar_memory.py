"""Custom memory implementation with bugfixes and extensions.

ScholarInMemoryMemory is the ResearchClaw equivalent of CoPaw's
CoPawInMemoryMemory, providing:
- Extended InMemoryMemory with summary support
- State serialization / deserialization
- Research context injection
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Try to import agentscope components
try:
    from agentscope.agent._react_agent import _MemoryMark
    from agentscope.memory import InMemoryMemory
    from agentscope.message import Msg

    _AGENTSCOPE_AVAILABLE = True
except ImportError:
    _AGENTSCOPE_AVAILABLE = False

    class _MemoryMark:  # type: ignore[no-redef]
        COMPRESSED = "compressed"

    class InMemoryMemory:  # type: ignore[no-redef]
        """Placeholder when agentscope is not available."""

        pass

    class Msg:  # type: ignore[no-redef]
        """Placeholder."""

        pass


class ScholarInMemoryMemory(InMemoryMemory):
    """Extended InMemoryMemory with bugfixes and research summary support.

    Provides enhanced memory management for the Scholar agent including:
    - Compressed summary prepending for conversation continuity
    - State dict serialization for persistence
    - Research context awareness
    """

    async def get_memory(
        self,
        mark: str | None = None,
        exclude_mark: str | None = _MemoryMark.COMPRESSED,
        prepend_summary: bool = True,
        **_kwargs: Any,
    ) -> list:
        """Get the messages from the memory by mark (if provided).

        Args:
            mark: Optional mark to filter messages.
            exclude_mark: Optional mark to exclude messages.
            prepend_summary: Whether to prepend compressed summary.
            **_kwargs: Additional keyword arguments (ignored).

        Returns:
            List of filtered messages.
        """
        if not (mark is None or isinstance(mark, str)):
            raise TypeError(
                f"The mark should be a string or None, but got {type(mark)}.",
            )

        if not (exclude_mark is None or isinstance(exclude_mark, str)):
            raise TypeError(
                f"The exclude_mark should be a string or None, but got "
                f"{type(exclude_mark)}.",
            )

        # Filter messages based on mark
        filtered_content = [
            (msg, marks)
            for msg, marks in self.content
            if mark is None or mark in marks
        ]

        # Further filter messages based on exclude_mark
        if exclude_mark is not None:
            filtered_content = [
                (msg, marks)
                for msg, marks in filtered_content
                if exclude_mark not in marks
            ]

        if prepend_summary and self._compressed_summary:
            previous_summary = f"""
<previous-summary>
{self._compressed_summary}
</previous-summary>
The above is a summary of our previous conversation.
Use it as context to maintain continuity in our research discussion.
                    """.strip()

            return [
                Msg(
                    "user",
                    previous_summary,
                    "user",
                ),
                *[msg for msg, _ in filtered_content],
            ]

        return [msg for msg, _ in filtered_content]

    def get_compressed_summary(self) -> str:
        """Get the compressed summary of the memory."""
        return self._compressed_summary

    def state_dict(self) -> dict:
        """Get the state dictionary for serialization."""
        return {
            "content": [[msg.to_dict(), marks] for msg, marks in self.content],
            "_compressed_summary": self._compressed_summary,
        }

    def load_state_dict(
        self,
        state_dict: dict,
        strict: bool = True,
    ) -> None:
        """Load the state dictionary for deserialization."""
        if strict and "content" not in state_dict:
            raise KeyError(
                "The state_dict does not contain 'content' key required for "
                "InMemoryMemory.",
            )

        self.content = []
        for item in state_dict.get("content", []):
            if isinstance(item, (tuple, list)) and len(item) == 2:
                msg_dict, marks = item
                msg = Msg.from_dict(msg_dict)
                self.content.append((msg, marks))

            elif isinstance(item, dict):
                # For compatibility with older versions
                msg = Msg.from_dict(item)
                self.content.append((msg, []))

            else:
                raise ValueError(
                    "Invalid item format in state_dict for InMemoryMemory.",
                )

        self._compressed_summary = state_dict.get(
            "_compressed_summary",
            "",
        )
