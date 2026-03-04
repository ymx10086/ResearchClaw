"""System command handler for ScholarAgent.

Processes ``/``-prefixed commands such as ``/new``, ``/compact``, ``/clear``,
``/history``, ``/papers``, ``/refs``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .react_agent import ScholarAgent

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handle slash-commands in the chat.

    Supported commands
    ------------------
    /new, /start      Start a new conversation (summarises the old one in background)
    /compact           Compress conversation memory
    /clear             Clear all history and summaries
    /history           Show conversation statistics
    /compact_str       Show current compact summary
    /papers            List recently discussed papers
    /refs              Show current reference library summary
    /help              Show available commands
    """

    def __init__(self, agent: ScholarAgent) -> None:
        self.agent = agent
        self._commands: dict[str, Any] = {
            "/new": self._cmd_new,
            "/start": self._cmd_new,
            "/compact": self._cmd_compact,
            "/clear": self._cmd_clear,
            "/history": self._cmd_history,
            "/compact_str": self._cmd_compact_str,
            "/papers": self._cmd_papers,
            "/refs": self._cmd_refs,
            "/help": self._cmd_help,
        }

    def handle(self, message: str) -> Optional[str]:
        """Try to handle *message* as a command.

        Returns
        -------
        str or None
            The command response, or *None* if *message* is not a known
            command (in which case normal agent processing should continue).
        """
        parts = message.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in self._commands:
            try:
                return self._commands[cmd](args)
            except Exception:
                logger.exception("Error executing command %s", cmd)
                return f"⚠️ Error executing command `{cmd}`. Check logs for details."

        return None  # Not a command — continue normal processing

    # ── Commands ────────────────────────────────────────────────────────

    def _cmd_new(self, args: str) -> str:
        """Start a new conversation."""
        self.agent.memory.new_session()
        return (
            "🔬 Started a new research session.\n\n"
            "Previous conversation has been archived. "
            "How can I help with your research today?"
        )

    def _cmd_compact(self, args: str) -> str:
        """Compress conversation memory."""
        stats_before = self.agent.memory.get_stats()
        self.agent.memory.compact()
        stats_after = self.agent.memory.get_stats()

        return (
            f"📦 Memory compacted.\n\n"
            f"- Messages before: {stats_before['message_count']}\n"
            f"- Messages after: {stats_after['message_count']}\n"
            f"- Summary length: {len(self.agent.memory.compact_summary)} chars"
        )

    def _cmd_clear(self, args: str) -> str:
        """Clear all history."""
        self.agent.memory.clear()
        return "🧹 All conversation history and summaries have been cleared."

    def _cmd_history(self, args: str) -> str:
        """Show conversation statistics."""
        stats = self.agent.memory.get_stats()
        return (
            f"📊 **Conversation Statistics**\n\n"
            f"- Session messages: {stats['message_count']}\n"
            f"- Total sessions: {stats['session_count']}\n"
            f"- Has compact summary: {'Yes' if stats['has_summary'] else 'No'}\n"
            f"- Research notes: {stats.get('note_count', 0)}\n"
            f"- Papers discussed: {stats.get('paper_count', 0)}"
        )

    def _cmd_compact_str(self, args: str) -> str:
        """Show the current compact summary."""
        summary = self.agent.memory.compact_summary
        if not summary:
            return "No compact summary available yet."
        return f"📋 **Current compact summary:**\n\n{summary}"

    def _cmd_papers(self, args: str) -> str:
        """List recently discussed papers."""
        papers = self.agent.memory.get_discussed_papers()
        if not papers:
            return "No papers have been discussed in this session yet."

        lines = ["📄 **Recently discussed papers:**\n"]
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "Untitled")
            authors = ", ".join(paper.get("authors", [])[:3])
            year = paper.get("year", "")
            lines.append(f"{i}. **{title}** ({authors}, {year})")

        return "\n".join(lines)

    def _cmd_refs(self, args: str) -> str:
        """Show reference library summary."""
        try:
            from ..constant import REFERENCES_DIR
            from pathlib import Path

            refs_dir = Path(REFERENCES_DIR)
            bib_files = (
                list(refs_dir.glob("*.bib")) if refs_dir.exists() else []
            )

            if not bib_files:
                return (
                    "📚 No reference library found.\n\n"
                    "Use `bibtex_add_entry` or search for papers to start building "
                    "your library."
                )

            total_entries = 0
            for bib_file in bib_files:
                content = bib_file.read_text(encoding="utf-8")
                total_entries += content.count("@")

            return (
                f"📚 **Reference Library**\n\n"
                f"- BibTeX files: {len(bib_files)}\n"
                f"- Total entries: ~{total_entries}\n"
                f"- Location: `{refs_dir}`"
            )
        except Exception:
            return "⚠️ Could not read reference library."

    def _cmd_help(self, args: str) -> str:
        """Show available commands."""
        return (
            "🔬 **Available Commands**\n\n"
            "| Command | Description |\n"
            "|---------|-------------|\n"
            "| `/new` | Start a new research session |\n"
            "| `/compact` | Compress conversation memory |\n"
            "| `/clear` | Clear all history |\n"
            "| `/history` | Show conversation statistics |\n"
            "| `/papers` | List recently discussed papers |\n"
            "| `/refs` | Show reference library summary |\n"
            "| `/compact_str` | Show current memory summary |\n"
            "| `/help` | Show this help message |"
        )
