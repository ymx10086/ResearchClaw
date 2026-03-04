"""Built-in tools for ResearchClaw.

Includes all core tools (file I/O, shell, browser, search) plus
research-specific tools (ArXiv, Semantic Scholar, BibTeX, etc.).
"""

from .file_io import (
    read_file,
    write_file,
    edit_file,
)
from .file_search import (
    grep_search,
    glob_search,
)
from .shell import run_shell
from .send_file import send_file
from .browser_control import browse_url
from .browser_snapshot import build_role_snapshot_from_aria
from .desktop_screenshot import desktop_screenshot
from .memory_search import memory_search
from .get_current_time import get_current_time

__all__ = [
    # File I/O
    "read_file",
    "write_file",
    "edit_file",
    # File search
    "grep_search",
    "glob_search",
    # Shell
    "run_shell",
    # Browser
    "browse_url",
    "build_role_snapshot_from_aria",
    "desktop_screenshot",
    # Memory
    "memory_search",
    # Utilities
    "send_file",
    "get_current_time",
]
