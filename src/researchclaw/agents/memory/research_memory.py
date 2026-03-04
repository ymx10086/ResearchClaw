"""Research memory system.

Provides persistent memory for research sessions, including conversation
history, discussed papers, and research notes.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ...constant import MEMORY_DIR, MEMORY_COMPACT_KEEP_RECENT

logger = logging.getLogger(__name__)


class ResearchMemory:
    """Persistent memory for the ScholarAgent.

    Stores conversation history, research notes, discussed papers,
    and compact summaries across sessions.

    Parameters
    ----------
    working_dir:
        Base working directory (default ``~/.researchclaw``).
    """

    def __init__(self, working_dir: str) -> None:
        self.working_dir = working_dir
        self.memory_dir = Path(MEMORY_DIR)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._messages: list[dict[str, str]] = []
        self._discussed_papers: list[dict[str, Any]] = []
        self._compact_summary: str = ""
        self._session_count: int = 0
        self._notes: list[dict[str, Any]] = []

        # Load existing state
        self._load_state()

    @property
    def compact_summary(self) -> str:
        """Current compact summary of previous conversations."""
        return self._compact_summary

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.

        Parameters
        ----------
        role:
            Message role (``"user"``, ``"assistant"``, ``"system"``).
        content:
            Message content.
        """
        self._messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            },
        )
        self._save_state()

    def get_recent_messages(
        self,
        count: Optional[int] = None,
    ) -> list[dict[str, str]]:
        """Get recent messages for the LLM context.

        Parameters
        ----------
        count:
            Number of recent messages. If None, returns all.

        Returns
        -------
        list[dict]
            Messages with ``role`` and ``content`` keys.
        """
        messages = self._messages if count is None else self._messages[-count:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def add_discussed_paper(self, paper: dict[str, Any]) -> None:
        """Record a paper that was discussed in conversation."""
        paper["discussed_at"] = datetime.now().isoformat()
        self._discussed_papers.append(paper)
        self._save_state()

    def get_discussed_papers(self) -> list[dict[str, Any]]:
        """Get papers discussed in current and recent sessions."""
        return self._discussed_papers[-20:]  # Last 20 papers

    def add_note(
        self,
        content: str,
        tags: Optional[list[str]] = None,
        title: str = "",
    ) -> None:
        """Add a research note.

        Parameters
        ----------
        content:
            Note content.
        tags:
            Optional tags for categorisation.
        title:
            Optional note title.
        """
        self._notes.append(
            {
                "title": title,
                "content": content,
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
            },
        )
        self._save_state()

    def new_session(self) -> None:
        """Start a new conversation session.

        Archives current messages and generates a compact summary.
        """
        if self._messages:
            # Generate summary of current session
            summary_parts = []
            if self._compact_summary:
                summary_parts.append(self._compact_summary)

            # Simple summary: extract key topics
            user_msgs = [
                m["content"] for m in self._messages if m["role"] == "user"
            ]
            if user_msgs:
                topics = "; ".join(user_msgs[:5])
                summary_parts.append(
                    f"Session {self._session_count + 1}: Topics discussed: {topics[:500]}",
                )

            self._compact_summary = "\n".join(summary_parts)

        self._messages = []
        self._session_count += 1
        self._save_state()

    def compact(self) -> None:
        """Compress conversation memory.

        Keeps the most recent messages and summarises older ones.
        """
        if len(self._messages) <= MEMORY_COMPACT_KEEP_RECENT:
            return

        older = self._messages[:-MEMORY_COMPACT_KEEP_RECENT]
        recent = self._messages[-MEMORY_COMPACT_KEEP_RECENT:]

        # Build a summary of older messages
        summary_parts = []
        if self._compact_summary:
            summary_parts.append(self._compact_summary)

        user_msgs = [m["content"] for m in older if m["role"] == "user"]
        asst_msgs = [m["content"] for m in older if m["role"] == "assistant"]

        if user_msgs:
            summary_parts.append(
                f"User asked about: {'; '.join(m[:100] for m in user_msgs[:10])}",
            )
        if asst_msgs:
            summary_parts.append(
                f"Assistant covered: {'; '.join(m[:100] for m in asst_msgs[:5])}",
            )

        self._compact_summary = "\n".join(summary_parts)
        self._messages = recent
        self._save_state()

    def clear(self) -> None:
        """Clear all memory."""
        self._messages = []
        self._compact_summary = ""
        self._discussed_papers = []
        self._notes = []
        self._save_state()

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "message_count": len(self._messages),
            "session_count": self._session_count,
            "has_summary": bool(self._compact_summary),
            "paper_count": len(self._discussed_papers),
            "note_count": len(self._notes),
        }

    def search(
        self,
        query: str,
        search_type: str = "all",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search through memory.

        Parameters
        ----------
        query:
            Search query.
        search_type:
            ``"all"``, ``"notes"``, ``"conversations"``, ``"papers"``.
        max_results:
            Maximum results.
        """
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        if search_type in ("all", "conversations"):
            for msg in self._messages:
                if query_lower in msg["content"].lower():
                    results.append(
                        {
                            "content": msg["content"][:500],
                            "source": "conversation",
                            "role": msg["role"],
                            "timestamp": msg.get("timestamp", ""),
                        },
                    )

        if search_type in ("all", "notes"):
            for note in self._notes:
                searchable = (
                    f"{note.get('title', '')} {note['content']}".lower()
                )
                if query_lower in searchable:
                    results.append(
                        {
                            "content": note["content"][:500],
                            "source": "note",
                            "title": note.get("title", ""),
                            "tags": note.get("tags", []),
                            "timestamp": note.get("created_at", ""),
                        },
                    )

        if search_type in ("all", "papers"):
            for paper in self._discussed_papers:
                searchable = f"{paper.get('title', '')} {' '.join(paper.get('authors', []))}".lower()
                if query_lower in searchable:
                    results.append(
                        {
                            "content": paper.get("title", ""),
                            "source": "paper",
                            "authors": paper.get("authors", []),
                            "year": paper.get("year"),
                            "timestamp": paper.get("discussed_at", ""),
                        },
                    )

        return results[:max_results]

    # ── Persistence ─────────────────────────────────────────────────────

    def _state_file(self) -> Path:
        return self.memory_dir / "memory_state.json"

    def _save_state(self) -> None:
        """Persist memory state to disk."""
        try:
            state = {
                "messages": self._messages[-1000:],  # Keep last 1000
                "compact_summary": self._compact_summary,
                "discussed_papers": self._discussed_papers[-100:],
                "session_count": self._session_count,
                "notes": self._notes[-500:],
            }
            self._state_file().write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.debug("Failed to save memory state", exc_info=True)

    def _load_state(self) -> None:
        """Load memory state from disk."""
        state_file = self._state_file()
        if not state_file.exists():
            return

        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self._messages = state.get("messages", [])
            self._compact_summary = state.get("compact_summary", "")
            self._discussed_papers = state.get("discussed_papers", [])
            self._session_count = state.get("session_count", 0)
            self._notes = state.get("notes", [])
        except Exception:
            logger.debug("Failed to load memory state", exc_info=True)
