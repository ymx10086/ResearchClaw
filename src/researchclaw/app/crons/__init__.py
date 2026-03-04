"""Cron jobs package – scheduled research tasks.

Provides:
- CronManager: APScheduler-based job scheduling with persistence
- CronExecutor: Job execution engine
- Cron job models (CronJobSpec, CronJobState, etc.)
- Job repository (BaseJobRepository, JsonJobRepository)
- API router for cron endpoints
- Heartbeat support
"""
from .manager import CronManager
from .executor import CronExecutor
from .api import router
from .models import (
    CronJobSpec,
    CronJobState,
    CronJobView,
    ScheduleSpec,
    DispatchSpec,
    DispatchTarget,
    JobRuntimeSpec,
    JobsFile,
)
from .repo import BaseJobRepository, JsonJobRepository

__all__ = [
    # Core classes
    "CronManager",
    "CronExecutor",
    # API
    "router",
    # Models
    "CronJobSpec",
    "CronJobState",
    "CronJobView",
    "ScheduleSpec",
    "DispatchSpec",
    "DispatchTarget",
    "JobRuntimeSpec",
    "JobsFile",
    # Repository
    "BaseJobRepository",
    "JsonJobRepository",
]
