"""Global constants for ResearchClaw.

All paths and configuration values can be overridden via environment variables
prefixed with ``RESEARCHCLAW_``.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Environment variable names ──────────────────────────────────────────────

LOG_LEVEL_ENV = "RESEARCHCLAW_LOG_LEVEL"

# ── Working directory ───────────────────────────────────────────────────────

WORKING_DIR: str = os.environ.get(
    "RESEARCHCLAW_WORKING_DIR",
    str(Path.home() / ".researchclaw"),
)

SECRET_DIR: str = os.environ.get(
    "RESEARCHCLAW_SECRET_DIR",
    str(Path(f"{WORKING_DIR}.secret")),
)

# ── Core data files (relative to WORKING_DIR) ──────────────────────────────

JOBS_FILE: str = os.environ.get("RESEARCHCLAW_JOBS_FILE", "jobs.json")
CHATS_FILE: str = os.environ.get("RESEARCHCLAW_CHATS_FILE", "chats.json")
CONFIG_FILE: str = os.environ.get("RESEARCHCLAW_CONFIG_FILE", "config.json")
ENV_FILE: str = os.environ.get("RESEARCHCLAW_ENV_FILE", ".env")

# ── Skills directories ──────────────────────────────────────────────────────

ACTIVE_SKILLS_DIR: str = os.environ.get(
    "RESEARCHCLAW_ACTIVE_SKILLS_DIR",
    str(Path(WORKING_DIR) / "active_skills"),
)
CUSTOMIZED_SKILLS_DIR: str = os.environ.get(
    "RESEARCHCLAW_CUSTOMIZED_SKILLS_DIR",
    str(Path(WORKING_DIR) / "customized_skills"),
)

# ── Research-specific directories ───────────────────────────────────────────

RESEARCH_DIR: str = os.environ.get(
    "RESEARCHCLAW_RESEARCH_DIR",
    str(Path(WORKING_DIR) / "research"),
)
RESEARCH_STATE_FILE: str = os.environ.get(
    "RESEARCHCLAW_RESEARCH_STATE_FILE",
    "state.json",
)
MEMORY_DIR: str = os.environ.get(
    "RESEARCHCLAW_MEMORY_DIR",
    str(Path(WORKING_DIR) / "memory"),
)
PAPERS_DIR: str = os.environ.get(
    "RESEARCHCLAW_PAPERS_DIR",
    str(Path(WORKING_DIR) / "papers"),
)
REFERENCES_DIR: str = os.environ.get(
    "RESEARCHCLAW_REFERENCES_DIR",
    str(Path(WORKING_DIR) / "references"),
)
EXPERIMENTS_DIR: str = os.environ.get(
    "RESEARCHCLAW_EXPERIMENTS_DIR",
    str(Path(WORKING_DIR) / "experiments"),
)
MD_FILES_DIR: str = os.environ.get(
    "RESEARCHCLAW_MD_FILES_DIR",
    str(Path(WORKING_DIR) / "md_files"),
)
DRAFTS_DIR: str = os.environ.get(
    "RESEARCHCLAW_DRAFTS_DIR",
    str(Path(WORKING_DIR) / "drafts"),
)
EXAMPLES_DIR: str = os.environ.get(
    "RESEARCHCLAW_EXAMPLES_DIR",
    str(Path(WORKING_DIR) / "examples"),
)
MODELS_DIR: str = os.environ.get(
    "RESEARCHCLAW_MODELS_DIR",
    str(Path(WORKING_DIR) / "models"),
)
CUSTOM_CHANNELS_DIR: str = os.environ.get(
    "RESEARCHCLAW_CUSTOM_CHANNELS_DIR",
    str(Path(WORKING_DIR) / "custom_channels"),
)

# ── Memory compaction ──────────────────────────────────────────────────────

MEMORY_COMPACT_KEEP_RECENT: int = int(
    os.environ.get("RESEARCHCLAW_MEMORY_COMPACT_KEEP_RECENT", "3"),
)
MEMORY_COMPACT_RATIO: float = float(
    os.environ.get("RESEARCHCLAW_MEMORY_COMPACT_RATIO", "0.7"),
)

# ── Heartbeat / Cron defaults ──────────────────────────────────────────────

HEARTBEAT_INTERVAL_MINUTES: int = int(
    os.environ.get("RESEARCHCLAW_HEARTBEAT_INTERVAL", "60"),
)
HEARTBEAT_ENABLED: bool = (
    os.environ.get("RESEARCHCLAW_HEARTBEAT_ENABLED", "true").lower() == "true"
)

# ── Paper digest defaults ──────────────────────────────────────────────────

PAPER_DIGEST_HOUR: int = int(
    os.environ.get("RESEARCHCLAW_PAPER_DIGEST_HOUR", "8"),
)
PAPER_DIGEST_ENABLED: bool = (
    os.environ.get("RESEARCHCLAW_PAPER_DIGEST_ENABLED", "false").lower()
    == "true"
)

# ── Research workflow automation defaults ──────────────────────────────────

RESEARCH_FOLLOWUP_ENABLED: bool = (
    os.environ.get("RESEARCHCLAW_RESEARCH_FOLLOWUP_ENABLED", "true").lower()
    == "true"
)
RESEARCH_FOLLOWUP_INTERVAL_MINUTES: int = int(
    os.environ.get("RESEARCHCLAW_RESEARCH_FOLLOWUP_INTERVAL_MINUTES", "30"),
)
RESEARCH_WORKFLOW_STALE_HOURS: int = int(
    os.environ.get("RESEARCHCLAW_RESEARCH_WORKFLOW_STALE_HOURS", "24"),
)

# ── Server configuration ──────────────────────────────────────────────────

DEFAULT_HOST: str = os.environ.get("RESEARCHCLAW_HOST", "127.0.0.1")
DEFAULT_PORT: int = int(os.environ.get("RESEARCHCLAW_PORT", "8088"))

DOCS_ENABLED: bool = (
    os.environ.get("RESEARCHCLAW_DOCS_ENABLED", "false").lower() == "true"
)
CORS_ORIGINS: str = os.environ.get("RESEARCHCLAW_CORS_ORIGINS", "")

# ── Agent defaults ─────────────────────────────────────────────────────────

AGENT_NAME: str = "Scholar"
DEFAULT_MAX_ITERS: int = 50
DEFAULT_MAX_INPUT_TOKENS: int = 128_000

# ── Default LLM ───────────────────────────────────────────────────────────

DEFAULT_MODEL_NAME: str = os.environ.get(
    "RESEARCHCLAW_DEFAULT_MODEL",
    "gpt-4o",
)

# ── Skills Hub ─────────────────────────────────────────────────────────────

SKILLS_HUB_URL: str = os.environ.get(
    "RESEARCHCLAW_SKILLS_HUB_URL",
    "https://hub.researchclaw.io",
)
SKILLS_HUB_TIMEOUT: int = int(
    os.environ.get("RESEARCHCLAW_SKILLS_HUB_TIMEOUT", "15"),
)
SKILLS_HUB_RETRIES: int = int(
    os.environ.get("RESEARCHCLAW_SKILLS_HUB_RETRIES", "3"),
)

# ── Reference file defaults ───────────────────────────────────────────────

DEFAULT_BIB_FILE: str = "references.bib"
