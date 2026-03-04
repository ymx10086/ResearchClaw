"""System prompt construction for ScholarAgent.

Reads Markdown profile files from the working directory to build a
research-oriented system prompt. Falls back to a sensible default when
the required files are missing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..constant import WORKING_DIR

logger = logging.getLogger(__name__)

# ── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_SYS_PROMPT = """\
You are **Scholar**, an AI research assistant created by ResearchClaw.

Your mission is to help academic researchers with their scientific workflow:
- Searching and discovering relevant papers (ArXiv, Semantic Scholar, Google Scholar)
- Reading, summarizing, and critically analyzing research papers
- Managing references and BibTeX citations
- Performing data analysis and creating publication-quality visualizations
- Assisting with LaTeX writing and literature reviews
- Tracking experiments and maintaining research notes
- Staying up-to-date with the latest publications in the user's fields of interest

Guidelines:
- Always cite sources when referring to specific papers or findings
- Be precise with scientific terminology
- When summarizing papers, highlight methodology, key findings, and limitations
- For data analysis, explain statistical methods and assumptions
- Provide BibTeX entries when recommending papers
- Respect the user's research domain expertise — assist, don't patronize
- When uncertain about scientific claims, clearly state the uncertainty

You have access to various research tools. Use them proactively to help the user.
"""

# ── Prompt file configuration ──────────────────────────────────────────────


@dataclass
class PromptFileSpec:
    """Specification for a single prompt file."""

    filename: str
    required: bool = True


@dataclass
class PromptConfig:
    """Ordered list of Markdown files that compose the system prompt."""

    files: list[PromptFileSpec] = field(
        default_factory=lambda: [
            PromptFileSpec("AGENTS.md", required=True),
            PromptFileSpec("SOUL.md", required=True),
            PromptFileSpec("PROFILE.md", required=False),
            PromptFileSpec("RESEARCH_AREAS.md", required=False),
        ],
    )


# ── Builder ─────────────────────────────────────────────────────────────────

_YAML_FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


class PromptBuilder:
    """Build the system prompt from Markdown files in a directory."""

    def __init__(
        self,
        directory: str | Path,
        config: Optional[PromptConfig] = None,
    ) -> None:
        self.directory = Path(directory)
        self.config = config or PromptConfig()

    def build(self) -> str:
        """Read and concatenate prompt files.

        Returns the concatenated Markdown content, or
        :data:`DEFAULT_SYS_PROMPT` if any required file is missing.
        """
        parts: list[str] = []
        for spec in self.config.files:
            path = self.directory / spec.filename
            if not path.is_file():
                if spec.required:
                    logger.warning(
                        "Required prompt file missing: %s – using default prompt",
                        path,
                    )
                    return DEFAULT_SYS_PROMPT
                continue

            text = path.read_text(encoding="utf-8")
            # Strip optional YAML front-matter
            text = _YAML_FRONT_MATTER.sub("", text).strip()
            parts.append(f"# {spec.filename}\n\n{text}")

        if not parts:
            return DEFAULT_SYS_PROMPT

        return "\n\n---\n\n".join(parts)


# ── Convenience functions ───────────────────────────────────────────────────


def build_system_prompt_from_working_dir() -> str:
    """Build the system prompt using files in :data:`WORKING_DIR`."""
    return PromptBuilder(WORKING_DIR).build()


def build_bootstrap_guidance(language: str = "en") -> str:
    """Return first-run guidance that helps the user configure Scholar.

    Parameters
    ----------
    language:
        ``"en"`` for English, ``"zh"`` for Chinese.
    """
    if language.startswith("zh"):
        return (
            "你好！我是 **Scholar**，你的 AI 科研助手。🔬\n\n"
            "在开始之前，我想了解一些关于你的信息：\n\n"
            "1. **你的研究领域**是什么？（例如：机器学习、生物信息学、量子物理）\n"
            "2. **你目前的研究方向**是什么？\n"
            "3. 你希望我用**中文**还是**英文**与你交流？\n"
            "4. 你有**常用的论文数据库偏好**吗？（ArXiv / Semantic Scholar / Google Scholar）\n"
            "5. 你是否有**正在进行的项目**需要我帮助追踪？\n\n"
            "你可以随时通过编辑 `~/.researchclaw/PROFILE.md` 来更新你的偏好。"
        )
    return (
        "Hello! I'm **Scholar**, your AI research assistant. 🔬\n\n"
        "Before we begin, I'd like to learn a few things about you:\n\n"
        "1. What is your **research field**? (e.g., Machine Learning, Bioinformatics, Quantum Physics)\n"
        "2. What are your **current research interests**?\n"
        "3. Which **language** do you prefer for our conversations?\n"
        "4. Do you have a **preferred paper database**? (ArXiv / Semantic Scholar / Google Scholar)\n"
        "5. Do you have any **ongoing projects** you'd like me to help track?\n\n"
        "You can update your preferences anytime by editing `~/.researchclaw/PROFILE.md`."
    )
