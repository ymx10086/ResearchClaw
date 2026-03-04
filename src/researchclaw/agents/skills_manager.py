"""Skills manager – manage the lifecycle of research skills.

Three-tier skill system:
1. **builtin** — shipped with the package under ``agents/skills/``
2. **customized** — user's working dir ``custom_skills/``
3. **active** — actual skills loaded by the agent ``active_skills/``

Key improvements over CoPaw:
- SKILL.md frontmatter parsing (name, description, emoji, requires)
- Directory tree building / comparison for efficient sync
- Path traversal protection on ``load_skill_file``
- Selective sync with ``skill_names`` filter + ``force`` flag
- ``create_skill`` with nested references/scripts tree creation
"""

from __future__ import annotations

import filecmp
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..constant import ACTIVE_SKILLS_DIR, CUSTOMIZED_SKILLS_DIR

logger = logging.getLogger(__name__)

# Built-in skills directory (shipped with the package)
_BUILTIN_SKILLS_DIR = Path(__file__).parent / "skills"


# ── Models ─────────────────────────────────────────────────────────


class SkillInfo(BaseModel):
    """Information about a skill."""

    name: str
    description: str = ""
    emoji: str = ""
    source: str = "builtin"  # "builtin", "customized", "hub"
    path: str = ""
    enabled: bool = True
    version: str = "0.1.0"
    content: str = ""  # full SKILL.md text
    references: Dict[str, Any] = Field(default_factory=dict)  # nested tree
    scripts: Dict[str, Any] = Field(default_factory=dict)  # nested tree
    requires: Dict[str, Any] = Field(default_factory=dict)


# ── Frontmatter parsing ───────────────────────────────────────────


def _parse_skill_md(text: str) -> Dict[str, Any]:
    """Parse SKILL.md header lines for metadata.

    Supports simple ``- key: value`` format at the top of the file
    (compatible with CoPaw's frontmatter convention).
    """
    meta: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:]
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()
            continue
        # Stop at first non-metadata line
        if not line.startswith("-") and meta:
            break
    return meta


# ── Directory tree helpers ─────────────────────────────────────────


def _build_directory_tree(directory: Path) -> Dict[str, Any]:
    """Recursively build ``{filename: None, dirname: {nested}}`` tree."""
    tree: Dict[str, Any] = {}
    if not directory.is_dir():
        return tree
    for entry in sorted(directory.iterdir()):
        if entry.name.startswith((".", "__pycache__")):
            continue
        if entry.is_file():
            tree[entry.name] = None
        elif entry.is_dir():
            tree[entry.name] = _build_directory_tree(entry)
    return tree


def _create_files_from_tree(
    base_dir: Path,
    tree: Dict[str, Any],
    contents: Optional[Dict[str, str]] = None,
) -> None:
    """Create files/directories from a nested tree structure.

    ``contents`` maps relative path → file content (text).
    Files not in ``contents`` are created empty.
    """
    contents = contents or {}
    for name, subtree in tree.items():
        path = base_dir / name
        if subtree is None:
            # File
            rel = (
                str(path.relative_to(base_dir))
                if base_dir != path.parent
                else name
            )
            text = contents.get(rel, "")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        else:
            # Directory
            path.mkdir(parents=True, exist_ok=True)
            sub_contents = {
                k[len(name) + 1 :]: v
                for k, v in contents.items()
                if k.startswith(name + "/")
            }
            _create_files_from_tree(path, subtree, sub_contents)


def _is_directory_same(dir1: Path, dir2: Path) -> bool:
    """Recursively compare two directories for identical content."""
    if not dir1.is_dir() or not dir2.is_dir():
        return False
    cmp = filecmp.dircmp(str(dir1), str(dir2))
    return _compare_dircmp(cmp)


def _compare_dircmp(cmp: filecmp.dircmp) -> bool:  # type: ignore[type-arg]
    """Helper: check dircmp result recursively."""
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    for sub_cmp in cmp.subdirs.values():
        if not _compare_dircmp(sub_cmp):
            return False
    return True


# ── Safe path helpers ──────────────────────────────────────────────


def _safe_path_parts(rel_path: str) -> Optional[List[str]]:
    """Validate a relative path: no ``..``, no absolute, no \\."""
    if not rel_path:
        return None
    parts = rel_path.replace("\\", "/").split("/")
    for p in parts:
        if p in (".", "..", "") or "/" in p or "\\" in p:
            return None
    return parts


# ── Core functions ─────────────────────────────────────────────────


def list_available_skills() -> List[SkillInfo]:
    """List all available skills (builtin + customised + active status)."""
    skills: Dict[str, SkillInfo] = {}

    # 1. Built-in skills
    if _BUILTIN_SKILLS_DIR.is_dir():
        for skill_dir in sorted(_BUILTIN_SKILLS_DIR.iterdir()):
            if skill_dir.is_dir() and not skill_dir.name.startswith(
                (".", "_"),
            ):
                info = _read_skill_info(skill_dir, source="builtin")
                skills[info.name] = info

    # 2. Customised skills (override builtin)
    custom_dir = Path(CUSTOMIZED_SKILLS_DIR)
    if custom_dir.is_dir():
        for skill_dir in sorted(custom_dir.iterdir()):
            if skill_dir.is_dir() and not skill_dir.name.startswith(
                (".", "_"),
            ):
                info = _read_skill_info(skill_dir, source="customized")
                skills[info.name] = info

    # 3. Mark active skills
    active_dir = Path(ACTIVE_SKILLS_DIR)
    if active_dir.is_dir():
        active_names = {
            d.name
            for d in active_dir.iterdir()
            if d.is_dir() and not d.name.startswith((".", "_"))
        }
        for name in skills:
            skills[name].enabled = name in active_names

    return sorted(skills.values(), key=lambda s: s.name)


def list_active_skills() -> List[str]:
    """Return names of currently active (enabled) skills."""
    active_dir = Path(ACTIVE_SKILLS_DIR)
    if not active_dir.is_dir():
        return []
    return sorted(
        d.name
        for d in active_dir.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    )


def sync_skills_to_working_dir(
    skill_names: Optional[List[str]] = None,
    force: bool = False,
) -> int:
    """Synchronise builtin and customised skills to the active directory.

    Parameters
    ----------
    skill_names:
        If provided, only sync these skills. Otherwise sync all.
    force:
        If True, overwrite even if destination already exists and is identical.

    Returns
    -------
    int
        Number of skills synced.
    """
    active_dir = Path(ACTIVE_SKILLS_DIR)
    active_dir.mkdir(parents=True, exist_ok=True)

    synced = 0

    # Collect source directories: builtin + customized override
    sources: Dict[str, Path] = {}

    if _BUILTIN_SKILLS_DIR.is_dir():
        for skill_dir in _BUILTIN_SKILLS_DIR.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith(
                (".", "_"),
            ):
                if skill_names is None or skill_dir.name in skill_names:
                    sources[skill_dir.name] = skill_dir

    custom_dir = Path(CUSTOMIZED_SKILLS_DIR)
    if custom_dir.is_dir():
        for skill_dir in custom_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith(
                (".", "_"),
            ):
                if skill_names is None or skill_dir.name in skill_names:
                    sources[skill_dir.name] = skill_dir  # override builtin

    for name, src in sources.items():
        dest = active_dir / name
        if dest.exists() and not force:
            if _is_directory_same(src, dest):
                continue  # skip unchanged
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        synced += 1

    logger.info("Synced %d skills to active directory", synced)
    return synced


def sync_skills_from_active_to_customized(
    skill_names: Optional[List[str]] = None,
) -> int:
    """Save modified active skills back to the customised directory.

    Skips skills whose active copy is identical to the builtin version.
    """
    active_dir = Path(ACTIVE_SKILLS_DIR)
    custom_dir = Path(CUSTOMIZED_SKILLS_DIR)
    custom_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    if not active_dir.is_dir():
        return saved

    for skill_dir in active_dir.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
            continue
        if skill_names and skill_dir.name not in skill_names:
            continue

        # Skip if identical to builtin (no user modifications)
        builtin_src = _BUILTIN_SKILLS_DIR / skill_dir.name
        if builtin_src.is_dir() and _is_directory_same(skill_dir, builtin_src):
            continue

        dest = custom_dir / skill_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)
        saved += 1

    return saved


def create_skill(
    name: str,
    content: str,
    *,
    overwrite: bool = False,
    references: Optional[Dict[str, Any]] = None,
    scripts: Optional[Dict[str, Any]] = None,
    extra_files: Optional[Dict[str, str]] = None,
) -> SkillInfo:
    """Create a new skill in the customized directory.

    Parameters
    ----------
    name:
        Skill name (directory name).
    content:
        SKILL.md content (must include name + description in header).
    overwrite:
        If True, replace existing skill.
    references:
        Nested tree for ``references/`` subdirectory.
    scripts:
        Nested tree for ``scripts/`` subdirectory.
    extra_files:
        Flat ``{relative_path: file_content}`` for additional files.
    """
    custom_dir = Path(CUSTOMIZED_SKILLS_DIR)
    dest = custom_dir / name

    if dest.exists() and not overwrite:
        raise FileExistsError(
            f"Skill '{name}' already exists. Use overwrite=True to replace.",
        )

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # Write SKILL.md
    (dest / "SKILL.md").write_text(content, encoding="utf-8")

    # Create references tree
    if references:
        refs_dir = dest / "references"
        refs_dir.mkdir(exist_ok=True)
        _create_files_from_tree(refs_dir, references, extra_files)

    # Create scripts tree
    if scripts:
        scripts_dir = dest / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        _create_files_from_tree(scripts_dir, scripts, extra_files)

    # Extra files (flat paths)
    if extra_files:
        for rel_path, file_content in extra_files.items():
            parts = _safe_path_parts(rel_path)
            if not parts:
                logger.warning("Skipping unsafe path: %s", rel_path)
                continue
            fpath = dest / rel_path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(file_content, encoding="utf-8")

    # Auto-sync to active
    active_dest = Path(ACTIVE_SKILLS_DIR) / name
    if active_dest.exists():
        shutil.rmtree(active_dest)
    shutil.copytree(dest, active_dest)

    return _read_skill_info(dest, source="customized")


def load_skill_file(
    skill_name: str,
    file_path: str,
    source: str = "active",
) -> Optional[str]:
    """Load a single file from a skill directory.

    Only allows files under ``references/`` or ``scripts/`` subdirectories,
    with path traversal protection.

    Parameters
    ----------
    skill_name:
        Name of the skill.
    file_path:
        Relative path within the skill (e.g. ``references/config.md``).
    source:
        One of ``"active"``, ``"customized"``, ``"builtin"``.
    """
    parts = _safe_path_parts(file_path)
    if not parts:
        logger.warning("Invalid file path: %s", file_path)
        return None

    # Must start with references/ or scripts/ or be SKILL.md
    allowed_prefixes = ("references", "scripts")
    if parts[0] not in allowed_prefixes and file_path != "SKILL.md":
        logger.warning(
            "Path not allowed: %s (must be under %s)",
            file_path,
            allowed_prefixes,
        )
        return None

    if source == "active":
        base = Path(ACTIVE_SKILLS_DIR) / skill_name
    elif source == "customized":
        base = Path(CUSTOMIZED_SKILLS_DIR) / skill_name
    else:
        base = _BUILTIN_SKILLS_DIR / skill_name

    fpath = base / file_path
    # Resolve and verify still under base
    try:
        resolved = fpath.resolve()
        base_resolved = base.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            logger.warning("Path traversal detected: %s", file_path)
            return None
    except Exception:
        return None

    if not fpath.is_file():
        return None

    return fpath.read_text(encoding="utf-8", errors="replace")


def ensure_skills_initialized() -> None:
    """Ensure the skill directories exist and are populated."""
    Path(ACTIVE_SKILLS_DIR).mkdir(parents=True, exist_ok=True)
    Path(CUSTOMIZED_SKILLS_DIR).mkdir(parents=True, exist_ok=True)
    sync_skills_to_working_dir()


def enable_skill(name: str) -> bool:
    """Enable a skill by copying it to the active directory."""
    sources = [
        Path(CUSTOMIZED_SKILLS_DIR) / name,
        _BUILTIN_SKILLS_DIR / name,
    ]
    for source in sources:
        if source.is_dir():
            dest = Path(ACTIVE_SKILLS_DIR) / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
            return True
    return False


def disable_skill(name: str) -> bool:
    """Disable a skill by removing it from the active directory."""
    dest = Path(ACTIVE_SKILLS_DIR) / name
    if dest.exists():
        shutil.rmtree(dest)
        return True
    return False


def delete_skill(name: str) -> bool:
    """Permanently delete a skill from the customized directory.

    Does NOT delete builtin skills. Also removes from active if present.
    """
    custom = Path(CUSTOMIZED_SKILLS_DIR) / name
    active = Path(ACTIVE_SKILLS_DIR) / name

    deleted = False
    if custom.exists():
        shutil.rmtree(custom)
        deleted = True
    if active.exists():
        shutil.rmtree(active)
        deleted = True

    return deleted


class SkillsManager:
    """Class-based interface for managing skills."""

    def list_all_skills(self) -> List[SkillInfo]:
        """List all skills (builtin + customized), syncing active→customized first."""
        sync_skills_from_active_to_customized()
        return list_available_skills()

    def list_available_skills(self) -> List[SkillInfo]:
        return list_available_skills()

    def list_active_skills(self) -> List[str]:
        return list_active_skills()

    def enable_skill(self, name: str) -> bool:
        return enable_skill(name)

    def disable_skill(self, name: str) -> bool:
        return disable_skill(name)

    def delete_skill(self, name: str) -> bool:
        return delete_skill(name)

    def create_skill(
        self,
        name: str,
        content: str,
        overwrite: bool = False,
        references: Optional[Dict[str, Any]] = None,
        scripts: Optional[Dict[str, Any]] = None,
        extra_files: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        info = create_skill(
            name,
            content,
            overwrite=overwrite,
            references=references,
            scripts=scripts,
            extra_files=extra_files,
        )
        return info.model_dump()

    def load_skill_file(
        self,
        skill_name: str,
        file_path: str,
        source: str = "active",
    ) -> Optional[str]:
        return load_skill_file(skill_name, file_path, source)


def _read_skill_info(skill_dir: Path, source: str = "builtin") -> SkillInfo:
    """Read skill metadata from its directory."""
    name = skill_dir.name
    description = ""
    emoji = ""
    content = ""
    requires: Dict[str, Any] = {}

    # Try SKILL.md first (primary metadata source)
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        meta = _parse_skill_md(content)
        description = meta.get("description", "")
        emoji = meta.get("emoji", "")
        if "requires" in meta:
            requires = {"raw": meta["requires"]}
        # Override name from frontmatter if present
        if meta.get("name"):
            name = meta["name"]

    if not description:
        readme = skill_dir / "README.md"
        if readme.exists():
            readme_text = readme.read_text(encoding="utf-8", errors="replace")
            for line in readme_text.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    description = line[:200]
                    break

    if not description:
        init_file = skill_dir / "__init__.py"
        if init_file.exists():
            init_text = init_file.read_text(encoding="utf-8", errors="replace")
            if '"""' in init_text:
                start = init_text.index('"""') + 3
                end = init_text.index('"""', start)
                description = init_text[start:end].strip()[:200]

    # Build references and scripts trees
    refs_dir = skill_dir / "references"
    scripts_dir = skill_dir / "scripts"
    references = _build_directory_tree(refs_dir) if refs_dir.is_dir() else {}
    scripts = (
        _build_directory_tree(scripts_dir) if scripts_dir.is_dir() else {}
    )

    return SkillInfo(
        name=name,
        description=description,
        emoji=emoji,
        source=source,
        path=str(skill_dir),
        content=content,
        references=references,
        scripts=scripts,
        requires=requires,
    )
