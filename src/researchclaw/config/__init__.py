"""Configuration package."""

from researchclaw.config.config import (
    get_heartbeat_config,
    get_heartbeat_query_path,
    load_config,
    save_config,
    update_last_dispatch,
)

__all__ = [
    "load_config",
    "save_config",
    "get_heartbeat_config",
    "get_heartbeat_query_path",
    "update_last_dispatch",
    "ConfigWatcher",
]


def __getattr__(name: str):
    if name == "ConfigWatcher":
        from researchclaw.config.watcher import ConfigWatcher

        return ConfigWatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
