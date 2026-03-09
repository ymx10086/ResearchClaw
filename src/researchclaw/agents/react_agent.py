"""ScholarAgent – the core ReAct agent for ResearchClaw.

Inherits from AgentScope's ReActAgent and extends it with research-specific
tools, skills, memory, and hooks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal, Optional

from ..constant import (
    ACTIVE_SKILLS_DIR,
    AGENT_NAME,
    DEFAULT_MAX_INPUT_TOKENS,
    DEFAULT_MAX_ITERS,
    WORKING_DIR,
)
from .skill_compat import (
    SkillDoc,
    build_skill_context_prompt,
    explain_skill_selection,
    parse_skill_doc,
    select_relevant_skills,
)

logger = logging.getLogger(__name__)

# Paths to built-in Markdown prompt files
_MD_FILES_DIR = Path(__file__).parent / "md_files"
NamesakeStrategy = Literal["override", "skip", "raise", "rename"]


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
        namesake_strategy: NamesakeStrategy = "skip",
    ) -> None:
        self.name = name
        self.working_dir = working_dir
        self.max_iters = max_iters
        self.max_input_tokens = max_input_tokens
        self.namesake_strategy: NamesakeStrategy = namesake_strategy

        # ── 1. Build toolkit ────────────────────────────────────────────
        self._tools: dict[str, Any] = {}
        self._skill_docs: list[SkillDoc] = []
        self._last_skill_debug: dict[str, Any] = {}
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

        # ── 7. Build tool schemas for OpenAI function calling ───────────
        self._tool_schemas: list[dict[str, Any]] = self._build_tool_schemas()

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
        from .tools.browser_control import browse_url, browser_use
        from .tools.data_analysis import (
            data_describe,
            data_query,
            plot_chart,
        )
        from .tools.cron_jobs import (
            cron_create_job,
            cron_delete_job,
            cron_get_job,
            cron_list_jobs,
            cron_pause_job,
            cron_resume_job,
            cron_run_job,
        )
        from .tools.file_io import (
            read_file,
            write_file,
            edit_file,
            append_file,
        )
        from .tools.get_current_time import get_current_time
        from .tools.latex_helper import latex_compile_check, latex_template
        from .tools.memory_search import memory_search
        from .tools.paper_reader import read_paper
        from .tools.semantic_scholar import semantic_scholar_search
        from .tools.send_file import send_file
        from .tools.copaw_compat import (
            execute_shell_command,
            send_file_to_user,
        )
        from .tools.skill_tools import skills_list, skills_read_file
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
            # Scheduling tools
            "cron_list_jobs": cron_list_jobs,
            "cron_get_job": cron_get_job,
            "cron_create_job": cron_create_job,
            "cron_delete_job": cron_delete_job,
            "cron_pause_job": cron_pause_job,
            "cron_resume_job": cron_resume_job,
            "cron_run_job": cron_run_job,
            # General tools
            "run_shell": run_shell,
            "execute_shell_command": execute_shell_command,
            "read_file": read_file,
            "write_file": write_file,
            "edit_file": edit_file,
            "append_file": append_file,
            "browse_url": browse_url,
            "browser_use": browser_use,
            "send_file": send_file,
            "send_file_to_user": send_file_to_user,
            "get_current_time": get_current_time,
            "memory_search": memory_search,
            "skills_list": skills_list,
            "skills_read_file": skills_read_file,
        }
        for tool_name, tool_fn in builtin.items():
            self._register_tool(tool_name, tool_fn, source="builtin")

    def _register_tool(self, name: str, func: Any, source: str = "") -> str:
        """Register a single tool with namesake strategy handling."""
        if name not in self._tools:
            self._tools[name] = func
            return name

        strategy = self.namesake_strategy
        prefix = f"{source} " if source else ""
        if strategy == "skip":
            logger.warning(
                "Skip duplicate tool '%s' from %s(source already exists)",
                name,
                prefix or "",
            )
            return name

        if strategy == "raise":
            raise ValueError(f"Duplicate tool '{name}' from {source}")

        if strategy == "rename":
            idx = 2
            renamed = f"{name}_{idx}"
            while renamed in self._tools:
                idx += 1
                renamed = f"{name}_{idx}"
            self._tools[renamed] = func
            logger.info("Renamed duplicate tool '%s' -> '%s'", name, renamed)
            return renamed

        # override
        self._tools[name] = func
        logger.info("Override tool '%s' from %s", name, source or "unknown")
        return name

    def _register_skills(self) -> None:
        """Load and register skills from the active_skills directory."""
        try:
            from .skills_manager import ensure_skills_initialized

            ensure_skills_initialized()
        except Exception:
            logger.warning(
                "Failed to initialize skills directory",
                exc_info=True,
            )
        skills_dir = Path(ACTIVE_SKILLS_DIR)
        if not skills_dir.is_dir():
            logger.debug("No active_skills directory found at %s", skills_dir)
            return

        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            self._load_skill_doc(skill_dir)
            self._load_skill(skill_dir)

    def _refresh_skill_docs(self) -> None:
        """Refresh SKILL.md metadata from active skills directory."""
        skills_dir = Path(ACTIVE_SKILLS_DIR)
        if not skills_dir.is_dir():
            self._skill_docs = []
            return

        refreshed: list[SkillDoc] = []
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            init_file = skill_dir / "__init__.py"
            main_file = skill_dir / "main.py"
            executable = bool(init_file.exists() or main_file.exists())
            try:
                parsed = parse_skill_doc(skill_dir, executable=executable)
                if parsed is not None:
                    refreshed.append(parsed)
            except Exception:
                logger.debug(
                    "Failed to refresh SKILL.md for %s",
                    skill_dir.name,
                    exc_info=True,
                )

        self._skill_docs = refreshed

    def _load_skill_doc(self, skill_dir: Path) -> None:
        """Load SKILL.md metadata for CoPaw-style doc-only skills."""
        init_file = skill_dir / "__init__.py"
        main_file = skill_dir / "main.py"
        executable = bool(init_file.exists() or main_file.exists())

        try:
            parsed = parse_skill_doc(skill_dir, executable=executable)
            if parsed is not None:
                self._skill_docs.append(parsed)
        except Exception:
            logger.exception(
                "Failed to parse SKILL.md for skill: %s",
                skill_dir.name,
            )

    def _load_skill(self, skill_dir: Path) -> None:
        """Load a single skill from its directory."""
        init_file = skill_dir / "__init__.py"
        main_file = skill_dir / "main.py"
        skill_file = main_file if main_file.exists() else init_file

        if not skill_file.exists():
            # CoPaw compatibility: doc-only skills are valid and loaded via
            # SKILL.md prompt guidance in _build_messages.
            logger.debug(
                "Skill %s has no Python entry point; treat as guidance-only skill",
                skill_dir.name,
            )
            return

        try:
            import importlib.util
            import sys

            # Use the canonical package path so that relative imports
            # (e.g. ``from ...tools.paper_reader``, ``from ....constant``)
            # resolve correctly against the installed researchclaw package.
            module_fqn = f"researchclaw.agents.skills.{skill_dir.name}"
            package_fqn = module_fqn  # __init__.py ⇒ module IS the package

            spec = importlib.util.spec_from_file_location(
                module_fqn,
                skill_file,
                submodule_search_locations=[str(skill_dir)],
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = package_fqn
                # Register in sys.modules so nested relative imports work
                sys.modules[module_fqn] = mod
                spec.loader.exec_module(mod)  # type: ignore[union-attr]

                # Convention: skills expose a `tools` dict or `register` function
                if hasattr(mod, "tools"):
                    for tool_name, tool_fn in mod.tools.items():
                        self._register_tool(
                            tool_name,
                            tool_fn,
                            source=f"skill:{skill_dir.name}",
                        )
                    logger.info(
                        "Loaded skill: %s (%d tools)",
                        skill_dir.name,
                        len(mod.tools),
                    )
                elif hasattr(mod, "register"):
                    new_tools = mod.register()
                    if isinstance(new_tools, dict):
                        for tool_name, tool_fn in new_tools.items():
                            self._register_tool(
                                tool_name,
                                tool_fn,
                                source=f"skill:{skill_dir.name}",
                            )
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
        changed = False
        for client in mcp_clients:
            try:
                tools = client.get_tools()
                if not isinstance(tools, dict):
                    logger.warning(
                        "MCP client returned non-dict tools: %s",
                        type(tools).__name__,
                    )
                    continue
                for tool_name, tool_fn in tools.items():
                    self._register_tool(
                        tool_name,
                        tool_fn,
                        source=f"mcp:{getattr(client, 'name', 'client')}",
                    )
                    changed = True
                logger.info("Registered MCP client with %d tools", len(tools))
            except Exception:
                logger.exception("Failed to register MCP client")
                # Best-effort recovery for stateful clients.
                try:
                    reconnect = getattr(client, "reconnect", None) or getattr(
                        client,
                        "connect",
                        None,
                    )
                    if callable(reconnect):
                        reconnect()
                        retry_tools = client.get_tools()
                        if isinstance(retry_tools, dict):
                            for tool_name, tool_fn in retry_tools.items():
                                self._register_tool(
                                    tool_name,
                                    tool_fn,
                                    source=f"mcp:{getattr(client, 'name', 'client')}:recovered",
                                )
                                changed = True
                            logger.info(
                                "Recovered MCP client and registered %d tools",
                                len(retry_tools),
                            )
                except Exception:
                    logger.debug("MCP client recovery failed", exc_info=True)
        if changed:
            self._tool_schemas = self._build_tool_schemas()

    # ── Reply ───────────────────────────────────────────────────────────

    def reply(
        self,
        message: str,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Process a user message and return a response.

        This method:
        1. Checks for system commands (``/compact``, ``/new``, etc.)
        2. Runs lifecycle hooks (bootstrap, memory compaction)
        3. Delegates to the ReAct reasoning loop

        Parameters
        ----------
        message:
            The user's input message.
        session_id:
            Optional session ID to tag memory messages.

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
        response = self._reasoning(message, session_id=session_id, **kwargs)

        # Run post-reply hooks
        for hook in self._hooks:
            if hasattr(hook, "post_reply"):
                hook.post_reply(message, response)

        return response

    def _reasoning(
        self,
        message: str,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> str:
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
        self.memory.add_message("user", message, session_id=session_id)

        # Build messages for the model
        messages = self._build_messages(user_message=message)

        # Prepare tool kwargs
        model_kwargs: dict[str, Any] = {}
        if self._tool_schemas:
            model_kwargs["tools"] = self._tool_schemas

        for iteration in range(self.max_iters):
            try:
                response = self.model(messages, **model_kwargs)

                # Check if the model wants to use a tool
                if hasattr(response, "tool_calls") and response.tool_calls:
                    # Add assistant message with tool_calls (required by OpenAI API)
                    # DeepSeek thinking mode requires reasoning_content in
                    # assistant messages that contain tool_calls.
                    # See: https://api-docs.deepseek.com/guides/thinking_mode#tool-calls
                    import json

                    assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": getattr(response, "content", None) or None,
                        "tool_calls": [],
                    }
                    _reasoning = getattr(response, "reasoning_content", None)
                    if _reasoning:
                        assistant_msg["reasoning_content"] = _reasoning
                    for tc in response.tool_calls:
                        tc_func = (
                            tc.function
                            if hasattr(tc, "function")
                            else tc.get("function", {})
                        )
                        tc_id = (
                            tc.id if hasattr(tc, "id") else tc.get("id", "")
                        )
                        tc_name = (
                            tc_func.name
                            if hasattr(tc_func, "name")
                            else tc_func.get("name", "")
                        )
                        tc_args = (
                            tc_func.arguments
                            if hasattr(tc_func, "arguments")
                            else tc_func.get("arguments", "")
                        )
                        assistant_msg["tool_calls"].append(
                            {
                                "id": tc_id,
                                "type": "function",
                                "function": {
                                    "name": tc_name,
                                    "arguments": tc_args,
                                },
                            },
                        )
                    messages.append(assistant_msg)

                    for tool_call in response.tool_calls:
                        tc_func = (
                            tool_call.function
                            if hasattr(tool_call, "function")
                            else tool_call.get("function", {})
                        )
                        tc_id = (
                            tool_call.id
                            if hasattr(tool_call, "id")
                            else tool_call.get("id", "")
                        )
                        tool_name = (
                            tc_func.name
                            if hasattr(tc_func, "name")
                            else tc_func.get("name", "")
                        )
                        tool_args_raw = (
                            tc_func.arguments
                            if hasattr(tc_func, "arguments")
                            else tc_func.get("arguments", "{}")
                        )

                        logger.info(
                            "[Tool Call] %s | args=%s",
                            tool_name,
                            str(tool_args_raw)[:500],
                        )

                        if tool_name in self._tools:
                            try:
                                tool_args = (
                                    json.loads(tool_args_raw)
                                    if isinstance(tool_args_raw, str)
                                    else tool_args_raw
                                )
                                result = self._tools[tool_name](**tool_args)
                                result_str = str(result)
                                logger.info(
                                    "[Tool Result] %s | result=%s",
                                    tool_name,
                                    result_str[:500],
                                )
                                messages.append(
                                    {
                                        "role": "tool",
                                        "content": result_str,
                                        "tool_call_id": tc_id,
                                    },
                                )
                            except Exception as e:
                                logger.exception(
                                    "[Tool Error] %s | %s",
                                    tool_name,
                                    e,
                                )
                                messages.append(
                                    {
                                        "role": "tool",
                                        "content": f"Tool error: {e}",
                                        "tool_call_id": tc_id,
                                    },
                                )
                        else:
                            logger.warning("[Tool Unknown] %s", tool_name)
                            messages.append(
                                {
                                    "role": "tool",
                                    "content": f"Unknown tool: {tool_name}",
                                    "tool_call_id": tc_id,
                                },
                            )
                    continue

                # No structured tool calls — check for text-format tool calls
                content = (
                    response.content
                    if hasattr(response, "content")
                    else str(response)
                )

                text_tool_calls = self._parse_text_tool_calls(content)
                if text_tool_calls:
                    import json as _json2

                    logger.info(
                        "[Text Tool Call] Parsed %d tool call(s) from text output",
                        len(text_tool_calls),
                    )
                    # Build a synthetic assistant message for context
                    messages.append({"role": "assistant", "content": content})

                    tool_results_text: list[str] = []
                    for ttc in text_tool_calls:
                        t_name = ttc["name"]
                        t_args = ttc["arguments"]
                        logger.info(
                            "[Text Tool Call] %s | args=%s",
                            t_name,
                            str(t_args)[:500],
                        )

                        if t_name in self._tools:
                            try:
                                result = self._tools[t_name](**t_args)
                                result_str = str(result)
                                logger.info(
                                    "[Text Tool Result] %s | result=%s",
                                    t_name,
                                    result_str[:500],
                                )
                            except Exception as e:
                                logger.exception(
                                    "[Text Tool Error] %s | %s",
                                    t_name,
                                    e,
                                )
                                result_str = f"Tool error: {e}"
                        else:
                            logger.warning("[Text Tool Unknown] %s", t_name)
                            result_str = f"Unknown tool: {t_name}"

                        tool_results_text.append(
                            f"Tool `{t_name}` result:\n{result_str}",
                        )

                    # Feed tool results back as a user message so model can summarize
                    combined = "\n\n".join(tool_results_text)
                    messages.append({"role": "user", "content": combined})
                    continue

                # Truly final response — no tool calls at all
                self.memory.add_message(
                    "assistant",
                    content,
                    session_id=session_id,
                )
                return content

            except Exception as e:
                logger.exception("Error in reasoning iteration %d", iteration)
                error_msg = f"I encountered an error during reasoning: {e}"
                self.memory.add_message(
                    "assistant",
                    error_msg,
                    session_id=session_id,
                )
                return error_msg

        timeout_msg = (
            "I've reached the maximum number of reasoning steps. "
            "Please try breaking your request into smaller parts."
        )
        self.memory.add_message(
            "assistant",
            timeout_msg,
            session_id=session_id,
        )
        return timeout_msg

    def _build_messages(
        self,
        user_message: str | None = None,
    ) -> list[dict[str, str]]:
        """Build the message list for the LLM from memory and system prompt."""
        self._refresh_skill_docs()
        messages = [{"role": "system", "content": self.sys_prompt}]

        # CoPaw-style skill compatibility: inject skill guidance for current turn.
        # This allows doc-only skills (SKILL.md without Python entry points) to
        # shape behavior while keeping tools as the execution backend.
        if self._skill_docs:
            selection_debug = explain_skill_selection(
                query=user_message or "",
                skills=self._skill_docs,
            )
            selected_skills = select_relevant_skills(
                query=user_message or "",
                skills=self._skill_docs,
            )
            self._last_skill_debug = selection_debug
            skill_hint = build_skill_context_prompt(
                query=user_message or "",
                skills=self._skill_docs,
                selected_skills=selected_skills,
                selection_debug=selection_debug,
            )
            if skill_hint:
                messages.append({"role": "system", "content": skill_hint})

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

    def get_last_skill_debug(self) -> dict[str, Any]:
        """Return skill-selection debug info from the latest turn."""
        return dict(self._last_skill_debug)

    def get_skill_debug_for_query(self, query: str) -> dict[str, Any]:
        """Run skill selection for an arbitrary query and return debug details."""
        self._refresh_skill_docs()
        return explain_skill_selection(query=query, skills=self._skill_docs)

    def rebuild_sys_prompt(self) -> None:
        """Rebuild the system prompt from working directory files."""
        from .prompt import build_system_prompt_from_working_dir

        self.sys_prompt = build_system_prompt_from_working_dir()
        logger.info("System prompt rebuilt")

    @property
    def tool_names(self) -> list[str]:
        """Return the names of all registered tools."""
        return sorted(self._tools.keys())

    def _build_tool_schemas(self) -> list[dict[str, Any]]:
        """Generate OpenAI-compatible tool schemas from registered tools."""
        import inspect

        schemas: list[dict[str, Any]] = []
        _TYPE_MAP = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for name, func in self._tools.items():
            try:
                sig = inspect.signature(func)
                doc = inspect.getdoc(func) or ""
                # First line of docstring as description
                desc = doc.split("\n", maxsplit=1)[0].strip() if doc else name

                properties: dict[str, Any] = {}
                required: list[str] = []

                for pname, param in sig.parameters.items():
                    annotation = param.annotation
                    # Resolve Optional types
                    origin = getattr(annotation, "__origin__", None)
                    if origin is not None:
                        # e.g. Optional[str] -> str
                        args = getattr(annotation, "__args__", ())
                        if type(None) in args:
                            annotation = next(
                                (a for a in args if a is not type(None)),
                                str,
                            )
                        else:
                            annotation = args[0] if args else str

                    json_type = _TYPE_MAP.get(annotation, "string")
                    prop: dict[str, Any] = {"type": json_type}

                    # Add default value as description hint
                    if param.default is not inspect.Parameter.empty:
                        if param.default is not None:
                            prop["default"] = param.default
                    else:
                        required.append(pname)

                    properties[pname] = prop

                schema = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc[:1024],
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                }
                schemas.append(schema)
            except Exception:
                logger.debug(
                    "Could not build schema for tool: %s",
                    name,
                    exc_info=True,
                )

        logger.info("Built %d tool schemas for function calling", len(schemas))
        return schemas

    @staticmethod
    def _parse_text_tool_calls(content: str) -> list[dict[str, Any]]:
        """Parse text-format tool calls from model output.

        Some models don't support structured function calling and instead
        output tool calls in XML-like text formats such as::

            <FunctionCall> {'tool' => 'name', 'args' => ...} </FunctionCall>
            <tool_call>{"name": ..., "arguments": ...}</tool_call>

        Returns a list of ``{"name": str, "arguments": dict}`` dicts.
        """
        import re
        import json as _json

        results: list[dict[str, Any]] = []

        # ── Pattern 1a: <FunctionCall><invoke name="..."><parameter ...>...</parameter></invoke></FunctionCall>
        # Also handles bare <invoke> without outer <FunctionCall> wrapper
        invoke_blocks = re.findall(
            r"<invoke\s+name=[\"']([^\"']+)[\"']\s*>(.*?)</invoke>",
            content,
            re.DOTALL,
        )
        for tool_name, invoke_body in invoke_blocks:
            tool_name = tool_name.strip()
            params: dict[str, Any] = {}
            param_matches = re.findall(
                r'<parameter\s+name=["\']([^"\']+)["\']>(.*?)</parameter>',
                invoke_body,
                re.DOTALL,
            )
            for key, val in param_matches:
                val = val.strip()
                try:
                    params[key] = int(val)
                except ValueError:
                    try:
                        params[key] = float(val)
                    except ValueError:
                        params[key] = val
            logger.debug(
                "[_parse_text_tool_calls] invoke: name=%s, params=%s",
                tool_name,
                params,
            )
            results.append({"name": tool_name, "arguments": params})

        if results:
            return results

        # ── Pattern 1b: <FunctionCall> {'tool' => 'name', 'args' => ...} </FunctionCall>
        fc_blocks = re.findall(
            r"<FunctionCall>(.*?)</FunctionCall>",
            content,
            re.DOTALL,
        )
        for block in fc_blocks:
            # Extract tool name (both ' and " quotes, and => or : separators)
            name_m = re.search(
                r"""['"]?tool['"]?\s*(?:=>|:)\s*['"]([^'"]+)['"]""",
                block,
            )
            if not name_m:
                continue
            tool_name = name_m.group(1).strip()

            params = {}

            # Try extracting <param name="key">value</param>
            param_matches = re.findall(
                r'<param\s+name=["\']([^"\']+)["\']>(.*?)</param>',
                block,
                re.DOTALL,
            )
            for key, val in param_matches:
                val = val.strip()
                try:
                    params[key] = int(val)
                except ValueError:
                    try:
                        params[key] = float(val)
                    except ValueError:
                        params[key] = val

            # If no <param> found, try JSON-style args
            if not params:
                args_m = re.search(
                    r"""['"]?args['"]?\s*(?:=>|:)\s*(\{.*\})""",
                    block,
                    re.DOTALL,
                )
                if args_m:
                    try:
                        params = _json.loads(args_m.group(1))
                    except _json.JSONDecodeError:
                        # Try python-style dict
                        try:
                            import ast

                            params = ast.literal_eval(args_m.group(1))
                        except Exception:
                            pass

            logger.debug(
                "[_parse_text_tool_calls] FC block: name=%s, params=%s",
                tool_name,
                params,
            )
            results.append({"name": tool_name, "arguments": params})

        if results:
            return results

        # ── Pattern 2: <tool_call>{"name": "...", "arguments": {...}}</tool_call> ──
        tc_blocks = re.findall(
            r"<tool_call>\s*(.*?)\s*</tool_call>",
            content,
            re.DOTALL,
        )
        for block in tc_blocks:
            try:
                data = _json.loads(block)
                name = data.get("name", "")
                args = data.get("arguments", {})
                if name:
                    results.append({"name": name, "arguments": args})
            except _json.JSONDecodeError:
                pass

        if results:
            return results

        # ── Pattern 3: ```json {"name": "tool_name", "arguments": {...}} ``` ──
        json_blocks = re.findall(
            r"```(?:json)?\s*(\{[^`]*?\"name\"\s*:\s*\"[^`]*?\})\s*```",
            content,
            re.DOTALL,
        )
        for block in json_blocks:
            try:
                data = _json.loads(block)
                name = data.get("name", "")
                args = data.get("arguments", {})
                if name:
                    results.append({"name": name, "arguments": args})
            except _json.JSONDecodeError:
                pass

        return results

    # ── Streaming reply ─────────────────────────────────────────────────

    def reply_stream(
        self,
        message: str,
        session_id: str | None = None,
        **kwargs: Any,
    ):
        """Process a user message and yield streaming SSE event dicts.

        Yields dicts with ``type`` key:
        - ``{"type": "thinking", "content": "..."}``
        - ``{"type": "content", "content": "..."}``
        - ``{"type": "tool_call", "name": "...", "arguments": "..."}``
        - ``{"type": "tool_result", "name": "...", "result": "..."}``
        - ``{"type": "done", "content": "full text"}``
        - ``{"type": "error", "content": "..."}``
        """
        import json as _json

        # Check for system commands
        if message.strip().startswith("/"):
            cmd_result = self.command_handler.handle(message.strip())
            if cmd_result is not None:
                yield {"type": "content", "content": cmd_result}
                yield {"type": "done", "content": cmd_result}
                return

        # Run pre-reply hooks
        for hook in self._hooks:
            if hasattr(hook, "pre_reply"):
                message = hook.pre_reply(message)

        # Check model
        if self.model is None:
            err = (
                "No LLM model configured. Please run `researchclaw init` "
                "to set up your model provider."
            )
            yield {"type": "error", "content": err}
            return

        self.memory.add_message("user", message, session_id=session_id)
        messages = self._build_messages(user_message=message)
        full_content = ""

        # Prepare tool kwargs for model calls
        stream_model_kwargs: dict[str, Any] = {}
        if self._tool_schemas:
            stream_model_kwargs["tools"] = self._tool_schemas

        for iteration in range(self.max_iters):
            try:
                # If model supports streaming, use it
                if hasattr(self.model, "stream"):
                    accumulated_content = ""
                    accumulated_thinking = ""
                    tool_calls_in_turn: list[dict] = []

                    for event in self.model.stream(
                        messages,
                        **stream_model_kwargs,
                    ):
                        etype = event.get("type")

                        if etype == "thinking":
                            accumulated_thinking += event.get("content", "")
                            yield event

                        elif etype == "content":
                            accumulated_content += event["content"]
                            yield event

                        elif etype == "tool_call":
                            tool_calls_in_turn.append(event)
                            yield {
                                "type": "tool_call",
                                "name": event["name"],
                                "arguments": event.get("arguments", ""),
                            }

                        elif etype == "done":
                            pass  # handled below

                    # If there were tool calls, execute them
                    if tool_calls_in_turn:
                        # Add assistant message with tool calls to messages
                        # DeepSeek thinking mode requires reasoning_content in
                        # assistant messages that contain tool_calls.
                        # See: https://api-docs.deepseek.com/guides/thinking_mode#tool-calls
                        assistant_msg: dict[str, Any] = {
                            "role": "assistant",
                            "content": accumulated_content or None,
                            "tool_calls": [
                                {
                                    "id": tc.get(
                                        "id",
                                        f"call_{iteration}_{i}",
                                    ),
                                    "type": "function",
                                    "function": {
                                        "name": tc["name"],
                                        "arguments": tc.get("arguments", "{}"),
                                    },
                                }
                                for i, tc in enumerate(tool_calls_in_turn)
                            ],
                        }
                        if accumulated_thinking:
                            assistant_msg[
                                "reasoning_content"
                            ] = accumulated_thinking
                        messages.append(assistant_msg)

                        for tc in tool_calls_in_turn:
                            tool_name = tc["name"]
                            raw_args = tc.get("arguments", "{}")
                            call_id = tc.get("id", f"call_{iteration}")

                            logger.info(
                                "[Stream Tool Call] %s | args=%s",
                                tool_name,
                                str(raw_args)[:500],
                            )

                            if tool_name in self._tools:
                                try:
                                    tool_args = (
                                        _json.loads(raw_args)
                                        if isinstance(raw_args, str)
                                        else raw_args
                                    )
                                    result = self._tools[tool_name](
                                        **tool_args,
                                    )
                                    result_str = str(result)
                                    logger.info(
                                        "[Stream Tool Result] %s | result=%s",
                                        tool_name,
                                        result_str[:500],
                                    )
                                except Exception as e:
                                    logger.exception(
                                        "[Stream Tool Error] %s | %s",
                                        tool_name,
                                        e,
                                    )
                                    result_str = f"Tool error: {e}"
                            else:
                                result_str = f"Unknown tool: {tool_name}"

                            messages.append(
                                {
                                    "role": "tool",
                                    "content": result_str,
                                    "tool_call_id": call_id,
                                },
                            )

                            yield {
                                "type": "tool_result",
                                "name": tool_name,
                                "result": result_str[:2000],
                            }

                        # Continue reasoning loop
                        continue

                    # No structured tool calls — check text format
                    logger.debug(
                        "[Stream] Checking text tool calls in: %s",
                        accumulated_content[:1000],
                    )
                    text_tool_calls = self._parse_text_tool_calls(
                        accumulated_content,
                    )
                    if text_tool_calls:
                        logger.info(
                            "[Stream Text Tool Call] Parsed %d tool call(s) from text",
                            len(text_tool_calls),
                        )

                        # Strip tool-call XML from content shown to user
                        import re as _re

                        cleaned = _re.sub(
                            r"<FunctionCall>.*?</FunctionCall>",
                            "",
                            accumulated_content,
                            flags=_re.DOTALL,
                        )
                        cleaned = _re.sub(
                            r"<invoke\s+name=[\"'][^\"']+[\"']\s*>.*?</invoke>",
                            "",
                            cleaned,
                            flags=_re.DOTALL,
                        )
                        cleaned = cleaned.strip()

                        # Tell frontend to replace the displayed content
                        yield {
                            "type": "content_replace",
                            "content": cleaned,
                        }

                        messages.append(
                            {
                                "role": "assistant",
                                "content": accumulated_content,
                            },
                        )

                        tool_results_parts: list[str] = []
                        for ttc in text_tool_calls:
                            t_name = ttc["name"]
                            t_args = ttc["arguments"]
                            logger.info(
                                "[Stream Text Tool Call] %s | args=%s",
                                t_name,
                                str(t_args)[:500],
                            )
                            yield {
                                "type": "tool_call",
                                "name": t_name,
                                "arguments": _json.dumps(
                                    t_args,
                                    ensure_ascii=False,
                                ),
                            }

                            if t_name in self._tools:
                                try:
                                    result = self._tools[t_name](**t_args)
                                    result_str = str(result)
                                    logger.info(
                                        "[Stream Text Tool Result] %s | result=%s",
                                        t_name,
                                        result_str[:500],
                                    )
                                except Exception as e:
                                    logger.exception(
                                        "[Stream Text Tool Error] %s | %s",
                                        t_name,
                                        e,
                                    )
                                    result_str = f"Tool error: {e}"
                            else:
                                result_str = f"Unknown tool: {t_name}"

                            yield {
                                "type": "tool_result",
                                "name": t_name,
                                "result": result_str[:2000],
                            }
                            tool_results_parts.append(
                                f"Tool `{t_name}` result:\n{result_str}",
                            )

                        combined = "\n\n".join(tool_results_parts)
                        messages.append({"role": "user", "content": combined})
                        continue

                    # Truly final response
                    full_content = accumulated_content
                    break

                # Non-streaming fallback
                response = self.model(messages, **stream_model_kwargs)

                if hasattr(response, "tool_calls") and response.tool_calls:
                    # Add assistant message with tool_calls
                    ns_assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": getattr(response, "content", None) or None,
                        "tool_calls": [],
                    }
                    for tc in response.tool_calls:
                        tc_func = (
                            tc.function
                            if hasattr(tc, "function")
                            else tc.get("function", {})
                        )
                        tc_id = (
                            tc.id if hasattr(tc, "id") else tc.get("id", "")
                        )
                        tc_name = (
                            tc_func.name
                            if hasattr(tc_func, "name")
                            else tc_func.get("name", "")
                        )
                        tc_args = (
                            tc_func.arguments
                            if hasattr(tc_func, "arguments")
                            else tc_func.get("arguments", "")
                        )
                        ns_assistant_msg["tool_calls"].append(
                            {
                                "id": tc_id,
                                "type": "function",
                                "function": {
                                    "name": tc_name,
                                    "arguments": tc_args,
                                },
                            },
                        )
                    messages.append(ns_assistant_msg)

                    for tool_call in response.tool_calls:
                        tc_func = (
                            tool_call.function
                            if hasattr(tool_call, "function")
                            else tool_call.get("function", {})
                        )
                        tc_id = (
                            tool_call.id
                            if hasattr(tool_call, "id")
                            else tool_call.get("id", "")
                        )
                        tool_name = (
                            tc_func.name
                            if hasattr(tc_func, "name")
                            else tc_func.get("name", "")
                        )
                        tool_args_raw = (
                            tc_func.arguments
                            if hasattr(tc_func, "arguments")
                            else tc_func.get("arguments", "{}")
                        )

                        logger.info(
                            "[Stream Fallback Tool Call] %s | args=%s",
                            tool_name,
                            str(tool_args_raw)[:500],
                        )

                        yield {
                            "type": "tool_call",
                            "name": tool_name,
                            "arguments": str(tool_args_raw),
                        }

                        if tool_name in self._tools:
                            try:
                                tool_args = (
                                    _json.loads(tool_args_raw)
                                    if isinstance(tool_args_raw, str)
                                    else tool_args_raw
                                )
                                result = self._tools[tool_name](
                                    **tool_args,
                                )
                                result_str = str(result)
                                logger.info(
                                    "[Stream Fallback Tool Result] %s | result=%s",
                                    tool_name,
                                    result_str[:500],
                                )
                            except Exception as e:
                                logger.exception(
                                    "[Stream Fallback Tool Error] %s | %s",
                                    tool_name,
                                    e,
                                )
                                result_str = f"Tool error: {e}"
                        else:
                            logger.warning(
                                "[Stream Fallback Tool Unknown] %s",
                                tool_name,
                            )
                            result_str = f"Unknown tool: {tool_name}"

                        messages.append(
                            {
                                "role": "tool",
                                "content": result_str,
                                "tool_call_id": tc_id,
                            },
                        )

                        yield {
                            "type": "tool_result",
                            "name": tool_name,
                            "result": result_str[:2000],
                        }

                    continue

                content = (
                    response.content
                    if hasattr(response, "content")
                    else str(response)
                )
                full_content = content
                yield {"type": "content", "content": content}
                break

            except Exception as e:
                logger.exception("Error in streaming iteration %d", iteration)
                err = f"I encountered an error during reasoning: {e}"
                self.memory.add_message(
                    "assistant",
                    err,
                    session_id=session_id,
                )
                yield {"type": "error", "content": err}
                return

        else:
            # Reached max_iters
            full_content = (
                "I've reached the maximum number of reasoning steps. "
                "Please try breaking your request into smaller parts."
            )
            yield {"type": "content", "content": full_content}

        self.memory.add_message(
            "assistant",
            full_content,
            session_id=session_id,
        )
        yield {"type": "done", "content": full_content}

        # Run post-reply hooks
        for hook in self._hooks:
            if hasattr(hook, "post_reply"):
                hook.post_reply(message, full_content)
