"""Agent utilities package.

This package provides utilities for agent operations:
- file_handling: File download, management, and path utilities
- message_processing: Message content manipulation and validation
- tool_message_utils: Tool message validation and sanitization
- token_counting: Token counting for context window management
- setup_utils: Setup and initialization utilities
"""

# File handling
from .file_handling import (
    download_file_from_base64,
    download_file_from_url,
    safe_resolve_path,
    guess_mime_type,
    ensure_directory,
    get_file_size_str,
)

# Message processing
from .message_processing import (
    extract_text_from_message,
    is_first_user_interaction,
    prepend_to_message_content,
    process_file_and_media_blocks_in_message,
)

# Setup utilities
from .setup_utils import (
    copy_md_files,
    get_available_languages,
    get_md_file_list,
)

# Token counting
from .token_counting import (
    count_message_tokens,
    estimate_tokens,
    safe_count_message_tokens,
    safe_count_str_tokens,
)

# Tool message utilities
from .tool_message_utils import (
    _dedup_tool_blocks,
    _remove_invalid_tool_blocks,
    _repair_empty_tool_inputs,
    _sanitize_tool_messages,
    _truncate_text,
    check_valid_messages,
    extract_tool_ids,
    get_validation_report,
)

__all__ = [
    # File handling
    "download_file_from_base64",
    "download_file_from_url",
    "safe_resolve_path",
    "guess_mime_type",
    "ensure_directory",
    "get_file_size_str",
    # Message processing
    "process_file_and_media_blocks_in_message",
    "is_first_user_interaction",
    "prepend_to_message_content",
    "extract_text_from_message",
    # Setup utilities
    "copy_md_files",
    "get_available_languages",
    "get_md_file_list",
    # Token counting
    "estimate_tokens",
    "count_message_tokens",
    "safe_count_message_tokens",
    "safe_count_str_tokens",
    # Tool message utilities
    "_dedup_tool_blocks",
    "_remove_invalid_tool_blocks",
    "_repair_empty_tool_inputs",
    "_sanitize_tool_messages",
    "_truncate_text",
    "check_valid_messages",
    "extract_tool_ids",
    "get_validation_report",
]
