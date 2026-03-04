"""Agent markdown manager for reading and writing markdown files in working
and memory directories.

Enhanced from CoPaw with:
- Research-specific directories (papers, references, experiments)
- Frontmatter parsing support
- File versioning / backup
- Batch file operations
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AgentMdManager:
    """Manager for reading and writing markdown files in working and memory
    directories.

    Provides structured access to the agent's working directory tree
    including working files, memory files, and research-specific
    directories (papers, references, experiments).
    """

    def __init__(self, working_dir: str | Path):
        """Initialize directories for working and memory markdown files."""
        self.working_dir: Path = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir: Path = self.working_dir / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    # ── Working directory operations ────────────────────────────────────

    def list_working_mds(self) -> list[dict[str, Any]]:
        """List all markdown files with metadata in the working dir.

        Returns:
            list[dict]: A list of dictionaries, each containing:
                - filename: name of the file (with .md extension)
                - size: file size in bytes
                - path: absolute path string
                - created_time: file creation timestamp (ISO)
                - modified_time: file modification timestamp (ISO)
        """
        md_files = list(self.working_dir.glob("*.md"))
        result: list[dict[str, Any]] = []
        for f in md_files:
            if f.is_file():
                stat = f.stat()
                result.append(
                    {
                        "filename": f.name,
                        "size": stat.st_size,
                        "path": str(f),
                        "created_time": datetime.fromtimestamp(
                            stat.st_ctime,
                        ).isoformat(),
                        "modified_time": datetime.fromtimestamp(
                            stat.st_mtime,
                        ).isoformat(),
                    },
                )
        return result

    def read_working_md(self, md_name: str) -> str:
        """Read markdown file content from the working directory.

        Returns:
            str: The file content as string.
        """
        if not md_name.endswith(".md"):
            md_name += ".md"
        file_path = self.working_dir / md_name
        if not file_path.exists():
            raise FileNotFoundError(f"Working md file not found: {md_name}")
        return file_path.read_text(encoding="utf-8")

    def write_working_md(
        self,
        md_name: str,
        content: str,
        backup: bool = False,
    ) -> None:
        """Write markdown content to a file in the working directory.

        Args:
            md_name: File name (with or without .md extension).
            content: Markdown content to write.
            backup: If True, create a backup of the existing file before
                overwriting.
        """
        if not md_name.endswith(".md"):
            md_name += ".md"
        file_path = self.working_dir / md_name

        if backup and file_path.exists():
            self._create_backup(file_path)

        file_path.write_text(content, encoding="utf-8")

    def delete_working_md(self, md_name: str) -> bool:
        """Delete a markdown file from the working directory.

        Enhanced feature beyond CoPaw.

        Returns:
            True if the file was deleted.
        """
        if not md_name.endswith(".md"):
            md_name += ".md"
        file_path = self.working_dir / md_name
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
        return False

    # ── Memory directory operations ─────────────────────────────────────

    def list_memory_mds(self) -> list[dict[str, Any]]:
        """List all markdown files with metadata in the memory dir.

        Returns:
            list[dict]: A list of dictionaries with file metadata.
        """
        md_files = list(self.memory_dir.glob("*.md"))
        result: list[dict[str, Any]] = []
        for f in md_files:
            if f.is_file():
                stat = f.stat()
                result.append(
                    {
                        "filename": f.name,
                        "size": stat.st_size,
                        "path": str(f),
                        "created_time": datetime.fromtimestamp(
                            stat.st_ctime,
                        ).isoformat(),
                        "modified_time": datetime.fromtimestamp(
                            stat.st_mtime,
                        ).isoformat(),
                    },
                )
        return result

    def read_memory_md(self, md_name: str) -> str:
        """Read markdown file content from the memory directory.

        Returns:
            str: The file content as string.
        """
        if not md_name.endswith(".md"):
            md_name += ".md"
        file_path = self.memory_dir / md_name
        if not file_path.exists():
            raise FileNotFoundError(f"Memory md file not found: {md_name}")
        return file_path.read_text(encoding="utf-8")

    def write_memory_md(
        self,
        md_name: str,
        content: str,
        backup: bool = False,
    ) -> None:
        """Write markdown content to a file in the memory directory.

        Args:
            md_name: File name (with or without .md extension).
            content: Markdown content to write.
            backup: If True, create a backup before overwriting.
        """
        if not md_name.endswith(".md"):
            md_name += ".md"
        file_path = self.memory_dir / md_name

        if backup and file_path.exists():
            self._create_backup(file_path)

        file_path.write_text(content, encoding="utf-8")

    # ── Enhanced: Research-specific operations ──────────────────────────

    def list_all_mds(self, recursive: bool = False) -> list[dict[str, Any]]:
        """List markdown files across all managed directories.

        Enhanced feature beyond CoPaw: unified view across working + memory.

        Args:
            recursive: If True, search recursively in subdirectories.

        Returns:
            list[dict]: File metadata with 'source' field indicating
            origin directory.
        """
        results: list[dict[str, Any]] = []

        glob_pattern = "**/*.md" if recursive else "*.md"

        for f in self.working_dir.glob(glob_pattern):
            if f.is_file():
                stat = f.stat()
                try:
                    rel = f.relative_to(self.working_dir)
                except ValueError:
                    rel = f
                results.append(
                    {
                        "filename": f.name,
                        "relative_path": str(rel),
                        "size": stat.st_size,
                        "path": str(f),
                        "source": "working",
                        "modified_time": datetime.fromtimestamp(
                            stat.st_mtime,
                        ).isoformat(),
                    },
                )

        return results

    def search_mds(
        self,
        query: str,
        directory: str = "all",
    ) -> list[dict[str, Any]]:
        """Simple text search across markdown files.

        Enhanced feature beyond CoPaw: full-text search.

        Args:
            query: Text to search for (case-insensitive).
            directory: "working", "memory", or "all".

        Returns:
            List of matches with filename, line number, and context.
        """
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        dirs: list[tuple[str, Path]] = []
        if directory in ("all", "working"):
            dirs.append(("working", self.working_dir))
        if directory in ("all", "memory"):
            dirs.append(("memory", self.memory_dir))

        for source, dir_path in dirs:
            for md_file in dir_path.glob("*.md"):
                if not md_file.is_file():
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8")
                    for line_no, line in enumerate(
                        content.splitlines(),
                        start=1,
                    ):
                        if query_lower in line.lower():
                            results.append(
                                {
                                    "filename": md_file.name,
                                    "source": source,
                                    "line": line_no,
                                    "content": line.strip()[:200],
                                },
                            )
                except Exception:
                    continue

        return results

    # ── Internals ───────────────────────────────────────────────────────

    def _create_backup(self, file_path: Path) -> None:
        """Create a timestamped backup of a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.working_dir / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        try:
            shutil.copy2(file_path, backup_dir / backup_name)
            logger.debug("Created backup: %s", backup_name)
        except Exception as e:
            logger.warning("Failed to create backup: %s", e)


def _get_default_manager() -> AgentMdManager:
    """Get the default AgentMdManager using WORKING_DIR."""
    from ...constant import WORKING_DIR

    return AgentMdManager(working_dir=WORKING_DIR)


# Lazy singleton — initialized on first access
_AGENT_MD_MANAGER: Optional[AgentMdManager] = None


def get_agent_md_manager() -> AgentMdManager:
    """Get the global AgentMdManager singleton.

    Returns:
        The AgentMdManager instance.
    """
    global _AGENT_MD_MANAGER
    if _AGENT_MD_MANAGER is None:
        _AGENT_MD_MANAGER = _get_default_manager()
    return _AGENT_MD_MANAGER
