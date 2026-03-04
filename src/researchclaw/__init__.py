"""ResearchClaw – AI Research Assistant for Academic Researchers."""

import logging
import os
import time

from .constant import LOG_LEVEL_ENV
from .utils.logging import setup_logger

_t0 = time.perf_counter()
setup_logger(os.environ.get(LOG_LEVEL_ENV, "info"))
logging.getLogger(__name__).debug(
    "%.3fs package init",
    time.perf_counter() - _t0,
)
