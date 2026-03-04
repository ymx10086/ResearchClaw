"""Memory search tool for searching research notes and conversation history.

Supports two usage patterns:
- Factory function ``create_memory_search_tool(manager)`` for bound tools
- Standalone ``memory_search(query)`` for direct use

Research-specific search_type options: ``"all"``, ``"notes"``,
``"conversations"``, ``"papers"``, ``"citations"``.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def create_memory_search_tool(
    memory_manager: Any,
) -> Callable[..., Any]:
    """Create a memory_search tool function with bound memory_manager.

    Parameters
    ----------
    memory_manager:
        MemoryManager instance to use for searching.

    Returns
    -------
    callable
        An async function that can be registered as a tool.
    """

    async def memory_search(
        query: str,
        max_results: int = 10,
        min_score: float = 0.1,
        search_type: str = "all",
    ) -> Any:
        """Search MEMORY.md and memory/*.md files semantically.

        Use this tool before answering questions about prior research,
        decisions, dates, topics, preferences, or tasks. Returns top
        relevant snippets with file paths and line numbers.

        Parameters
        ----------
        query:
            The semantic search query to find relevant memory snippets.
        max_results:
            Maximum number of search results to return.
        min_score:
            Minimum similarity score for results.
        search_type:
            What to search: ``"all"`` (default), ``"notes"``,
            ``"conversations"``, ``"papers"``, ``"citations"``.

        Returns
        -------
        Search results formatted with paths, line numbers, and content.
        """
        if memory_manager is None:
            return {"error": "Memory manager is not enabled."}

        try:
            if hasattr(memory_manager, "memory_search"):
                return await memory_manager.memory_search(
                    query=query,
                    max_results=max_results,
                    min_score=min_score,
                )
            # Fallback to sync search
            return memory_manager.search(
                query,
                search_type=search_type,
                max_results=max_results,
            )
        except Exception as e:
            return {"error": f"Memory search failed: {e}"}

    return memory_search


def memory_search(
    query: str,
    search_type: str = "all",
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Standalone memory search (not bound to a manager).

    Parameters
    ----------
    query:
        Search query string.
    search_type:
        What to search: ``"all"`` (default), ``"notes"``,
        ``"conversations"``, ``"papers"``, ``"citations"``.
    max_results:
        Maximum number of results.

    Returns
    -------
    list[dict]
        Search results with ``content``, ``source``, ``timestamp``.
    """
    try:
        from ..memory.research_memory import ResearchMemory
        from ...constant import WORKING_DIR

        memory = ResearchMemory(working_dir=WORKING_DIR)
        return memory.search(
            query,
            search_type=search_type,
            max_results=max_results,
        )
    except Exception as e:
        logger.exception("Memory search failed")
        return [{"error": f"Memory search failed: {e}"}]
