# -*- coding: utf-8 -*-
# flake8: noqa: E501
"""System prompt building utilities.

This module provides utilities for building system prompts from
markdown configuration files in the working directory.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default fallback prompt
DEFAULT_SYS_PROMPT = """
You are a helpful assistant.
"""

# Backward compatibility alias
SYS_PROMPT = DEFAULT_SYS_PROMPT


class PromptConfig:
    """Configuration for system prompt building."""

    # Define file loading order: (filename, required)
    FILE_ORDER = [
        ("AGENTS.md", True),
        ("SOUL.md", True),
        ("PROFILE.md", False),
    ]


class PromptBuilder:
    """Builder for constructing system prompts from markdown files."""

    def __init__(self, working_dir: Path):
        """Initialize prompt builder.

        Args:
            working_dir: Directory containing markdown configuration files
        """
        self.working_dir = working_dir
        self.prompt_parts = []
        self.loaded_count = 0

    def _load_file(self, filename: str, required: bool) -> bool:
        """Load a single markdown file.

        Args:
            filename: Name of the file to load
            required: Whether the file is required

        Returns:
            True if file was loaded successfully, False otherwise
        """
        file_path = self.working_dir / filename

        if not file_path.exists():
            if required:
                logger.warning(
                    "%s not found in working directory (%s), using default prompt",
                    filename,
                    self.working_dir,
                )
                return False
            else:
                logger.debug("Optional file %s not found, skipping", filename)
                return True  # Not an error for optional files

        try:
            content = file_path.read_text(encoding="utf-8").strip()

            # Remove YAML frontmatter if present
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2].strip()

            if content:
                if self.prompt_parts:  # Add separator if not first section
                    self.prompt_parts.append("")
                # Add section header with filename
                self.prompt_parts.append(f"# {filename}")
                self.prompt_parts.append("")
                self.prompt_parts.append(content)
                self.loaded_count += 1
                logger.debug("Loaded %s", filename)
            else:
                logger.debug("Skipped empty file: %s", filename)

            return True

        except Exception as e:
            if required:
                logger.error(
                    "Failed to read required file %s: %s",
                    filename,
                    e,
                    exc_info=True,
                )
                return False
            else:
                logger.warning(
                    "Failed to read optional file %s: %s",
                    filename,
                    e,
                )
                return True  # Not fatal for optional files

    def build(self) -> str:
        """Build the system prompt from markdown files.

        Returns:
            Constructed system prompt string
        """
        for filename, required in PromptConfig.FILE_ORDER:
            if not self._load_file(filename, required):
                # Required file failed to load
                return DEFAULT_SYS_PROMPT

        if not self.prompt_parts:
            logger.warning("No content loaded from working directory")
            return DEFAULT_SYS_PROMPT

        # Join all parts with double newlines
        final_prompt = "\n\n".join(self.prompt_parts)

        logger.debug(
            "System prompt built from %d file(s), total length: %d chars",
            self.loaded_count,
            len(final_prompt),
        )

        return final_prompt


def build_system_prompt_from_working_dir() -> str:
    """
    Build system prompt by reading markdown files from working directory.

    This function constructs the system prompt by loading markdown files from
    WORKING_DIR (~/.researchclaw by default). These files define the agent's behavior,
    personality, and operational guidelines.

    Loading order and priority:
    1. AGENTS.md (required) - Detailed workflows, rules, and guidelines
    2. SOUL.md (required) - Core identity and behavioral principles
    3. PROFILE.md (optional) - Agent identity and user profile

    Returns:
        str: Constructed system prompt from markdown files.
             If required files don't exist, returns the default prompt.

    Example:
        If working_dir contains AGENTS.md, SOUL.md and PROFILE.md, they will be combined:
        "# AGENTS.md\\n\\n...\\n\\n# SOUL.md\\n\\n...\\n\\n# PROFILE.md\\n\\n..."
    """
    from ..constant import WORKING_DIR

    builder = PromptBuilder(working_dir=Path(WORKING_DIR))
    return builder.build()


def build_bootstrap_guidance(
    language: str = "zh",
) -> str:
    """Build bootstrap guidance message for first-time setup.

    Args:
        language: Language code (en/zh)

    Returns:
        Formatted bootstrap guidance message
    """
    if language == "en":
        return """# Workspace Setup Required

Your workspace is using default setup templates. Complete a quick setup before regular Q&A.

**What to do:**
1. Read `BOOTSTRAP.md`.
2. Help the user quickly customize `SOUL.md`, `AGENTS.md`, `PROFILE.md`, and `HEARTBEAT.md`.
3. Keep it practical: research goals, working style, timezone, channel preferences, and reminder cadence.
4. Write updates directly into the files.
5. After setup is complete, delete `BOOTSTRAP.md`.

If the user explicitly asks to skip setup, answer their request directly.

**Original user message:**
"""
    else:  # zh
        return """# 需要先完成工作区初始化

当前工作区仍是默认模板，请先完成一次简短初始化，再进入常规问答。

**你要做的事：**
1. 阅读 `BOOTSTRAP.md`。
2. 帮用户快速定制 `SOUL.md`、`AGENTS.md`、`PROFILE.md`、`HEARTBEAT.md`。
3. 聚焦实用信息：研究目标、协作方式、时区、通道偏好、提醒频率。
4. 直接把内容写入对应文件。
5. 初始化完成后删除 `BOOTSTRAP.md`。

如果用户明确表示跳过初始化，就直接回答其原始问题。

**用户的原始消息：**
"""


__all__ = [
    "build_system_prompt_from_working_dir",
    "build_bootstrap_guidance",
    "PromptBuilder",
    "PromptConfig",
    "DEFAULT_SYS_PROMPT",
    "SYS_PROMPT",  # Backward compatibility
]
