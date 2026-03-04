"""ScholarAgent – the core ReAct agent for ResearchClaw.

Inherits from AgentScope's ReActAgent and extends it with research-specific
tools, skills, memory, and hooks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from ..constant import (
    ACTIVE_SKILLS_DIR,
    AGENT_NAME,
    DEFAULT_MAX_INPUT_TOKENS,
    DEFAULT_MAX_ITERS,
    WORKING_DIR,
)

logger = logging.getLogger(__name__)

# Paths to built-in Markdown prompt files
_MD_FILES_DIR = Path(__file__).parent / "md_files"


class ScholarAgent:
    """AI Research Assistant agent based on the ReAct paradigm.

    This agent is specialised for academic research workflows:
    - Paper search and discovery (ArXiv, Semantic Scholar)
    - PDF reading and summarisation
    - Reference management (BibTeX)
    - Data analysis and visualisation
    - LaTeX writing assistance
    - Experiment tracking
    - Research note management

    Parameters
    ----------
    name:
        Agent display name (default ``"Scholar"``).
    llm_cfg:
        LLM configuration dict. If *None*, the active provider from
        ``config.json`` is used.
    max_iters:
        Maximum ReAct reasoning iterations per turn.
    max_input_tokens:
        Maximum context window size in tokens.
    working_dir:
        Path to the ResearchClaw working directory.
    """

    def __init__(
        self,
        name: str = AGENT_NAME,
        llm_cfg: Optional[dict[str, Any]] = None,
        max_iters: int = DEFAULT_MAX_ITERS,
        max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
        working_dir: str = WORKING_DIR,
    ) -> None:
        self.name = name
        self.working_dir = working_dir
        self.max_iters = max_iters
        self.max_input_tokens = max_input_tokens

        # ── 1. Build toolkit ────────────────────────────────────────────
        self._tools: dict[str, Any] = {}
        self._register_builtin_tools()
        self._register_skills()

        # ── 2. Build system prompt ──────────────────────────────────────
        from .prompt import build_system_prompt_from_working_dir

        self.sys_prompt = build_system_prompt_from_working_dir()

        # ── 3. Create model and formatter ───────────────────────────────
        from .model_factory import create_model_and_formatter

        self.model, self.formatter = create_model_and_formatter(llm_cfg)

        # ── 4. Initialise memory ────────────────────────────────────────
        self._init_memory()

        # ── 5. Register hooks ───────────────────────────────────────────
        self._hooks: list[Any] = []
        self._register_hooks()

        # ── 6. Command handler ──────────────────────────────────────────
        from .command_handler import CommandHandler

        self.command_handler = CommandHandler(self)

        logger.info("ScholarAgent initialised with %d tools", len(self._tools))

    # ── Tool registration ───────────────────────────────────────────────

    def _register_builtin_tools(self) -> None:
        """Register all built-in research tools."""
        from .tools.arxiv_search import arxiv_search
        from .tools.bibtex_manager import (
            bibtex_add_entry,
            bibtex_export,
            bibtex_search,
        )
        from .tools.browser_control import browse_url
        from .tools.data_analysis import (
            data_describe,
            data_query,
            plot_chart,
        )
        from .tools.file_io import read_file, write_file, edit_file
        from .tools.get_current_time import get_current_time
        from .tools.latex_helper import latex_compile_check, latex_template
        from .tools.memory_search import memory_search
        from .tools.paper_reader import read_paper
        from .tools.semantic_scholar import semantic_scholar_search
        from .tools.send_file import send_file
        from .tools.shell import run_shell

        builtin = {
            # Research tools
            "arxiv_search": arxiv_search,
            "semantic_scholar_search": semantic_scholar_search,
            "read_paper": read_paper,
            "bibtex_search": bibtex_search,
            "bibtex_add_entry": bibtex_add_entry,
            "bibtex_export": bibtex_export,
            "latex_template": latex_template,
            "latex_compile_check": latex_compile_check,
            # Data analysis
            "data_describe": data_describe,
            "data_query": data_query,
            "plot_chart": plot_chart,
            # General tools
            "run_shell": run_shell,
            "read_file": read_file,
            "write_file": write_file,
            "edit_file": edit_file,
            "browse_url": browse_url,
            "send_file": send_file,
            "get_current_time": get_current_time,
            "memory_search": memory_search,
        }
        self._tools.update(builtin)

    def _register_skills(self) -> None:
        """Load and register skills from the active_skills directory."""
        skills_dir = Path(ACTIVE_SKILLS_DIR)
        if not skills_dir.is_dir():
            logger.debug("No active_skills directory found at %s", skills_dir)
            return

        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            self._load_skill(skill_dir)

    def _load_skill(self, skill_dir: Path) -> None:
        """Load a single skill from its directory."""
        init_file = skill_dir / "__init__.py"
        main_file = skill_dir / "main.py"
        skill_file = main_file if main_file.exists() else init_file

        if not skill_file.exists():
            logger.warning(
                "Skill %s has no entry point, skipping",
                skill_dir.name,
            )
            return

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                f"researchclaw.skills.{skill_dir.name}",
                skill_file,
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]

                # Convention: skills expose a `tools` dict or `register` function
                if hasattr(mod, "tools"):
                    self._tools.update(mod.tools)
                    logger.info(
                        "Loaded skill: %s (%d tools)",
                        skill_dir.name,
                        len(mod.tools),
                    )
                elif hasattr(mod, "register"):
                    new_tools = mod.register()
                    if isinstance(new_tools, dict):
                        self._tools.update(new_tools)
                        logger.info(
                            "Loaded skill: %s (%d tools)",
                            skill_dir.name,
                            len(new_tools),
                        )
        except Exception:
            logger.exception("Failed to load skill: %s", skill_dir.name)

    # ── Memory ──────────────────────────────────────────────────────────

    def _init_memory(self) -> None:
        """Initialise the research memory system."""
        from .memory.research_memory import ResearchMemory

        self.memory = ResearchMemory(working_dir=self.working_dir)

    # ── Hooks ───────────────────────────────────────────────────────────

    def _register_hooks(self) -> None:
        """Register lifecycle hooks."""
        from .hooks.bootstrap import BootstrapHook
        from .hooks.memory_compaction import MemoryCompactionHook

        self._hooks.append(BootstrapHook(self))
        self._hooks.append(MemoryCompactionHook(self))

    # ── MCP clients ─────────────────────────────────────────────────────

    def register_mcp_clients(self, mcp_clients: list[Any]) -> None:
        """Register MCP (Model Context Protocol) clients to the toolkit."""
        for client in mcp_clients:
            try:
                tools = client.get_tools()
                self._tools.update(tools)
                logger.info("Registered MCP client with %d tools", len(tools))
            except Exception:
                logger.exception("Failed to register MCP client")

    # ── Reply ───────────────────────────────────────────────────────────

    def reply(self, message: str, **kwargs: Any) -> str:
        """Process a user message and return a response.

        This method:
        1. Checks for system commands (``/compact``, ``/new``, etc.)
        2. Runs lifecycle hooks (bootstrap, memory compaction)
        3. Delegates to the ReAct reasoning loop

        Parameters
        ----------
        message:
            The user's input message.

        Returns
        -------
        str
            The agent's response.
        """
        # Check for system commands
        if message.strip().startswith("/"):
            cmd_result = self.command_handler.handle(message.strip())
            if cmd_result is not None:
                return cmd_result

        # Run pre-reply hooks
        for hook in self._hooks:
            if hasattr(hook, "pre_reply"):
                message = hook.pre_reply(message)

        # ReAct reasoning loop
        response = self._reasoning(message, **kwargs)

        # Run post-reply hooks
        for hook in self._hooks:
            if hasattr(hook, "post_reply"):
                hook.post_reply(message, response)

        return response

    def _reasoning(self, message: str, **kwargs: Any) -> str:
        """Execute the ReAct reasoning loop.

        Iteratively calls the LLM with tool availability, executing tools
        as needed until the agent produces a final answer or reaches
        ``max_iters``.
        """
        if self.model is None:
            return (
                "No LLM model configured. Please run `researchclaw init` "
                "to set up your model provider."
            )

        # Add message to memory
        self.memory.add_message("user", message)

        # Build messages for the model
        messages = self._build_messages()

        for iteration in range(self.max_iters):
            try:
                response = self.model(messages)

                # Check if the model wants to use a tool
                if hasattr(response, "tool_calls") and response.tool_calls:
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("function", {}).get(
                            "name",
                            "",
                        )
                        tool_args = tool_call.get("function", {}).get(
                            "arguments",
                            {},
                        )

                        if tool_name in self._tools:
                            try:
                                import json

                                if isinstance(tool_args, str):
                                    tool_args = json.loads(tool_args)
                                result = self._tools[tool_name](**tool_args)
                                messages.append(
                                    {
                                        "role": "tool",
                                        "content": str(result),
                                        "tool_call_id": tool_call.get(
                                            "id",
                                            "",
                                        ),
                                    },
                                )
                            except Exception as e:
                                messages.append(
                                    {
                                        "role": "tool",
                                        "content": f"Tool error: {e}",
                                        "tool_call_id": tool_call.get(
                                            "id",
                                            "",
                                        ),
                                    },
                                )
                        else:
                            messages.append(
                                {
                                    "role": "tool",
                                    "content": f"Unknown tool: {tool_name}",
                                    "tool_call_id": tool_call.get("id", ""),
                                },
                            )
                    continue

                # No tool calls — this is the final response
                content = (
                    response.content
                    if hasattr(response, "content")
                    else str(response)
                )
                self.memory.add_message("assistant", content)
                return content

            except Exception as e:
                logger.exception("Error in reasoning iteration %d", iteration)
                error_msg = f"I encountered an error during reasoning: {e}"
                self.memory.add_message("assistant", error_msg)
                return error_msg

        timeout_msg = (
            "I've reached the maximum number of reasoning steps. "
            "Please try breaking your request into smaller parts."
        )
        self.memory.add_message("assistant", timeout_msg)
        return timeout_msg

    def _build_messages(self) -> list[dict[str, str]]:
        """Build the message list for the LLM from memory and system prompt."""
        messages = [{"role": "system", "content": self.sys_prompt}]

        # Add compact summary if available
        if self.memory.compact_summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"[Previous conversation summary]\n{self.memory.compact_summary}",
                },
            )

        # Add recent messages
        messages.extend(self.memory.get_recent_messages())
        return messages

    def rebuild_sys_prompt(self) -> None:
        """Rebuild the system prompt from working directory files."""
        from .prompt import build_system_prompt_from_working_dir

        self.sys_prompt = build_system_prompt_from_working_dir()
        logger.info("System prompt rebuilt")

    @property
    def tool_names(self) -> list[str]:
        """Return the names of all registered tools."""
        return sorted(self._tools.keys())
