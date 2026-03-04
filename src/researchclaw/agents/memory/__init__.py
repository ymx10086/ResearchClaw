"""Memory management module for ResearchClaw agents.

Provides:
- AgentMdManager: Markdown file management for working/memory dirs
- ResearchMemory: Persistent research session memory
- MemoryManager: High-level memory coordination
- ScholarInMemoryMemory: Extended in-memory storage with summary support
"""

from .agent_md_manager import AgentMdManager, get_agent_md_manager
from .memory_manager import MemoryManager
from .research_memory import ResearchMemory
from .scholar_memory import ScholarInMemoryMemory

__all__ = [
    "AgentMdManager",
    "get_agent_md_manager",
    "MemoryManager",
    "ResearchMemory",
    "ScholarInMemoryMemory",
]
