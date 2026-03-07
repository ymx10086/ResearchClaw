"""Bootstrap hook – runs on first message to guide the user through setup."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...config import load_config
from ..prompt import build_bootstrap_guidance
from ..utils import copy_md_files

if TYPE_CHECKING:
    from ..react_agent import ScholarAgent

logger = logging.getLogger(__name__)


class BootstrapHook:
    """First-run bootstrap hook for working-dir md files and guidance."""

    def __init__(self, agent: ScholarAgent) -> None:
        self.agent = agent
        self._bootstrapped = False
        self._md_initialized = False

    @property
    def _working_dir(self) -> Path:
        return Path(self.agent.working_dir)

    @property
    def _bootstrap_path(self) -> Path:
        return self._working_dir / "BOOTSTRAP.md"

    @property
    def _bootstrap_completed_flag(self) -> Path:
        return self._working_dir / ".bootstrap_completed"

    def _detect_language(self) -> str:
        try:
            cfg = load_config(self._working_dir / "config.json")
            language = str(cfg.get("language", "en") or "en").strip().lower()
            return "zh" if language.startswith("zh") else "en"
        except Exception:
            return "en"

    def _ensure_md_files(self) -> None:
        """Ensure key markdown templates exist in working directory."""
        if self._md_initialized:
            return
        self._md_initialized = True

        language = self._detect_language()
        include_bootstrap = not self._bootstrap_completed_flag.exists()
        copied = copy_md_files(
            language=language,
            skip_existing=True,
            target_dir=str(self._working_dir),
            include_bootstrap=include_bootstrap,
        )
        if copied:
            logger.info(
                "bootstrap init copied md files [%s]: %s",
                language,
                ", ".join(copied),
            )
            try:
                self.agent.rebuild_sys_prompt()
            except Exception:
                logger.debug("rebuild_sys_prompt failed after md init", exc_info=True)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()

    def _template_path(self, filename: str, language: str) -> Path:
        root = Path(__file__).resolve().parents[1] / "md_files"
        lang = "zh" if language.startswith("zh") else "en"
        candidate = root / lang / filename
        if candidate.exists():
            return candidate
        return root / "en" / filename

    def _is_default_template(self, filename: str, language: str) -> bool:
        path = self._working_dir / filename
        if not path.exists():
            return False
        tpl = self._template_path(filename, language)
        if not tpl.exists():
            return False
        try:
            current = self._normalize_text(path.read_text(encoding="utf-8"))
            template = self._normalize_text(tpl.read_text(encoding="utf-8"))
            return bool(current) and current == template
        except Exception:
            return False

    @staticmethod
    def _profile_has_placeholders(text: str) -> bool:
        # Empty key-value bullets, e.g. "- **Name:**" / "- **名字：**"
        if re.search(r"^\s*-\s*\*\*[^*]+\*\*\s*[：:]\s*$", text, flags=re.MULTILINE):
            return True
        # Placeholder hint lines in template, e.g. "*(...)*" / "*（...）*"
        if re.search(r"\*\s*[\(（].*?[\)）]\s*\*", text):
            return True
        return False

    def _core_file_gaps(self, language: str) -> list[str]:
        gaps: list[str] = []
        core_files = ["SOUL.md", "AGENTS.md", "PROFILE.md", "HEARTBEAT.md"]
        for filename in core_files:
            path = self._working_dir / filename
            if not path.exists():
                gaps.append(f"{filename} (missing)")
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                gaps.append(f"{filename} (unreadable)")
                continue
            if not content.strip():
                gaps.append(f"{filename} (empty)")
                continue
            if self._is_default_template(filename, language):
                gaps.append(f"{filename} (template not customized)")
                continue
            if filename == "PROFILE.md" and self._profile_has_placeholders(content):
                gaps.append(f"{filename} (contains placeholders)")
        return gaps

    @staticmethod
    def _build_gap_guidance(language: str, gaps: list[str]) -> str:
        joined = ", ".join(gaps)
        if language.startswith("zh"):
            return (
                "【初始化未完成】检测到以下工作区文件还未完成个性化配置："
                f"{joined}。\n"
                "请先完成这些文件（至少 SOUL.md、AGENTS.md、PROFILE.md、HEARTBEAT.md），"
                "再继续常规问答。你可以让我逐项帮你填写。"
            )
        return (
            "[Setup incomplete] The following workspace files still need customization: "
            f"{joined}.\n"
            "Please complete these files first (at least SOUL.md, AGENTS.md, PROFILE.md, HEARTBEAT.md) "
            "before regular Q&A. I can help you complete them step by step."
        )

    @staticmethod
    def _append_original_message(language: str, guidance: str, message: str) -> str:
        original = (message or "").strip()
        if not original:
            return guidance
        if language.startswith("zh"):
            return f"{guidance}\n\n【用户原始消息】\n{original}"
        return f"{guidance}\n\n[Original user message]\n{original}"

    def pre_reply(self, message: str) -> str:
        """Inject bootstrap guidance once and ensure md templates are present."""
        self._ensure_md_files()
        language = self._detect_language()

        gaps = self._core_file_gaps(language)
        if gaps:
            gap_guidance = self._build_gap_guidance(language, gaps)
            # Keep the user's original message visible to the model so it can
            # actually respond to setup replies instead of repeating guidance.
            return self._append_original_message(
                language,
                gap_guidance,
                message,
            )

        if self._bootstrapped:
            return message

        if self._bootstrap_completed_flag.exists():
            self._bootstrapped = True
            return message

        if not self._bootstrap_path.exists():
            self._bootstrapped = True
            return message

        self._bootstrapped = True
        guidance = build_bootstrap_guidance(language=language).strip()
        logger.info("First run detected — bootstrap guidance injected [%s]", language)

        try:
            self._bootstrap_completed_flag.touch(exist_ok=True)
        except Exception:
            logger.debug("touch .bootstrap_completed failed", exc_info=True)

        if not guidance:
            return message
        return f"{guidance}\n\n{message}"

    def should_show_guidance(self) -> bool:
        """Check if we should show first-run guidance."""
        self._ensure_md_files()
        return (
            self._bootstrap_path.exists()
            and not self._bootstrap_completed_flag.exists()
        )
