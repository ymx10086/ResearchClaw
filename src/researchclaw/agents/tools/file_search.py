"""File search tools: grep (content search) and glob (file discovery).

Provides workspace-wide file search capabilities for the agent,
including regex-based content search and glob pattern matching.

Enhanced from CoPaw with:
- Research-aware binary extension list (includes .bib, .tex awareness)
- Improved context line display
- Support for searching within specific file types
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

logger = None  # Lazy init


def _get_logger():
    global logger
    if logger is None:
        import logging

        logger = logging.getLogger(__name__)
    return logger


def _get_working_dir() -> Path:
    """Get the working directory, avoiding circular imports."""
    from ...constant import WORKING_DIR

    return Path(WORKING_DIR)


def _resolve_file_path(file_path: str) -> str:
    """Resolve file path: absolute as-is, relative from WORKING_DIR."""
    path = Path(file_path)
    if path.is_absolute():
        return str(path)
    return str(_get_working_dir() / file_path)


# Skip binary / large files
_BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".webp",
        ".svg",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".flac",
        ".wav",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".dat",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".a",
    },
)

_MAX_MATCHES = 200
_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB


def _is_text_file(path: Path) -> bool:
    """Heuristic check: skip known binary extensions and large files."""
    if path.suffix.lower() in _BINARY_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > _MAX_FILE_SIZE:
            return False
    except OSError:
        return False
    return True


def _relative_display(target: Path, root: Path) -> str:
    """Return a relative path string if possible, otherwise absolute."""
    try:
        return str(target.relative_to(root))
    except ValueError:
        return str(target)


async def grep_search(
    pattern: str,
    path: Optional[str] = None,
    is_regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 0,
    file_pattern: Optional[str] = None,
) -> dict:
    """Search file contents by pattern, recursively.

    Relative paths resolve from WORKING_DIR.
    Output format: ``path:line_number: content``.

    Args:
        pattern: Search string (or regex when is_regex=True).
        path: File or directory to search in. Defaults to WORKING_DIR.
        is_regex: Treat pattern as a regular expression.
        case_sensitive: Case-sensitive matching. Defaults to True.
        context_lines: Context lines before/after each match (like grep -C).
        file_pattern: Optional glob to filter files (e.g. "*.py", "*.bib").
            Enhanced feature beyond CoPaw.

    Returns:
        Dict with "matches" (str) and "count" (int).
    """
    if not pattern:
        return {"error": "No search `pattern` provided.", "count": 0}

    working_dir = _get_working_dir()
    search_root = Path(_resolve_file_path(path)) if path else working_dir

    if not search_root.exists():
        return {
            "error": f"The path {search_root} does not exist.",
            "count": 0,
        }

    # Compile regex
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        if is_regex:
            regex = re.compile(pattern, flags)
        else:
            regex = re.compile(re.escape(pattern), flags)
    except re.error as e:
        return {"error": f"Invalid regex pattern — {e}", "count": 0}

    matches: list[str] = []
    truncated = False

    # Collect files to search
    single_file = search_root.is_file()
    if single_file:
        files = [search_root]
    else:
        if file_pattern:
            files = sorted(
                f
                for f in search_root.rglob(file_pattern)
                if f.is_file() and _is_text_file(f)
            )
        else:
            files = sorted(
                f
                for f in search_root.rglob("*")
                if f.is_file() and _is_text_file(f)
            )

    for file_path_item in files:
        if truncated:
            break
        try:
            lines = file_path_item.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except OSError:
            continue

        for line_no, line in enumerate(lines, start=1):
            if regex.search(line):
                if len(matches) >= _MAX_MATCHES:
                    truncated = True
                    break

                # Context window
                start = max(0, line_no - 1 - context_lines)
                end = min(len(lines), line_no + context_lines)

                if single_file:
                    rel = file_path_item.name
                else:
                    rel = _relative_display(file_path_item, search_root)
                for ctx_idx in range(start, end):
                    prefix = ">" if ctx_idx == line_no - 1 else " "
                    matches.append(
                        f"{rel}:{ctx_idx + 1}:{prefix} {lines[ctx_idx]}",
                    )
                if context_lines > 0:
                    matches.append("---")

    if not matches:
        return {
            "matches": f"No matches found for pattern: {pattern}",
            "count": 0,
        }

    result = "\n".join(matches)
    count = sum(1 for m in matches if m.startswith(">") or ">" in m[:50])
    if truncated:
        result += f"\n\n(Results truncated at {_MAX_MATCHES} matches.)"

    return {"matches": result, "count": count}


async def glob_search(
    pattern: str,
    path: Optional[str] = None,
) -> dict:
    """Find files matching a glob pattern (e.g. ``"*.py"``, ``"**/*.bib"``).

    Relative paths resolve from WORKING_DIR.

    Args:
        pattern: Glob pattern to match.
        path: Root directory to search from. Defaults to WORKING_DIR.

    Returns:
        Dict with "files" (str) and "count" (int).
    """
    if not pattern:
        return {"error": "No glob `pattern` provided.", "count": 0}

    working_dir = _get_working_dir()
    search_root = Path(_resolve_file_path(path)) if path else working_dir

    if not search_root.exists():
        return {
            "error": f"The path {search_root} does not exist.",
            "count": 0,
        }

    if not search_root.is_dir():
        return {
            "error": f"The path {search_root} is not a directory.",
            "count": 0,
        }

    try:
        results: list[str] = []
        truncated = False
        for entry in sorted(search_root.glob(pattern)):
            rel = _relative_display(entry, search_root)
            suffix = "/" if entry.is_dir() else ""
            results.append(f"{rel}{suffix}")
            if len(results) >= _MAX_MATCHES:
                truncated = True
                break

        if not results:
            return {
                "files": f"No files matched pattern: {pattern}",
                "count": 0,
            }

        text = "\n".join(results)
        if truncated:
            text += f"\n\n(Results truncated at {_MAX_MATCHES} entries.)"

        return {"files": text, "count": len(results)}
    except Exception as e:
        return {"error": f"Glob search failed: {e}", "count": 0}
