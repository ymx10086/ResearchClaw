"""Setup and initialization utilities for agent configuration.

This module handles copying markdown configuration files to
the working directory. Enhanced from CoPaw with research-specific
template handling and validation.
"""
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def copy_md_files(
    language: str,
    skip_existing: bool = False,
    target_dir: Optional[str] = None,
) -> list[str]:
    """Copy md files from agents/md_files to working directory.

    Args:
        language: Language code (e.g. 'en', 'zh')
        skip_existing: If True, skip files that already exist in working dir.
        target_dir: Override target directory. Defaults to WORKING_DIR.

    Returns:
        List of copied file names.
    """
    from ...constant import WORKING_DIR

    working_dir = Path(target_dir) if target_dir else Path(WORKING_DIR)

    # Get md_files directory path with language subdirectory
    md_files_dir = Path(__file__).parent.parent / "md_files" / language

    if not md_files_dir.exists():
        logger.warning(
            "MD files directory not found: %s, falling back to 'en'",
            md_files_dir,
        )
        # Fallback to English if specified language not found
        md_files_dir = Path(__file__).parent.parent / "md_files" / "en"
        if not md_files_dir.exists():
            logger.error("Default 'en' md files not found either")
            return []

    # Ensure working directory exists
    working_dir.mkdir(parents=True, exist_ok=True)

    # Copy all .md files to working directory
    copied_files: list[str] = []
    for md_file in md_files_dir.glob("*.md"):
        target_file = working_dir / md_file.name
        if skip_existing and target_file.exists():
            logger.debug("Skipped existing md file: %s", md_file.name)
            continue
        try:
            shutil.copy2(md_file, target_file)
            logger.debug("Copied md file: %s", md_file.name)
            copied_files.append(md_file.name)
        except Exception as e:
            logger.error(
                "Failed to copy md file '%s': %s",
                md_file.name,
                e,
            )

    if copied_files:
        logger.debug(
            "Copied %d md file(s) [%s] to %s",
            len(copied_files),
            language,
            working_dir,
        )

    return copied_files


def get_available_languages() -> list[str]:
    """List available language codes for md_files.

    Enhanced feature beyond CoPaw.

    Returns:
        List of language codes (e.g. ['en', 'zh']).
    """
    md_files_root = Path(__file__).parent.parent / "md_files"
    if not md_files_root.exists():
        return []
    return sorted(
        d.name
        for d in md_files_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def get_md_file_list(language: str = "en") -> list[str]:
    """List available md template files for a language.

    Enhanced feature beyond CoPaw.

    Args:
        language: Language code.

    Returns:
        List of md file names available for the language.
    """
    md_files_dir = Path(__file__).parent.parent / "md_files" / language
    if not md_files_dir.exists():
        return []
    return sorted(f.name for f in md_files_dir.glob("*.md"))
