"""Cron job manager – APScheduler-based scheduling with persistence.

Supports both:
1. Persistent cron jobs (CronJobSpec from models.py) via APScheduler
2. Simple registered coroutine jobs for built-in tasks (heartbeat, etc.)

Includes heartbeat integration for 24x7 standby agent monitoring.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional

from ..console_push_store import push_store
from .executor import CronExecutor
from .heartbeat import parse_heartbeat_every, run_heartbeat_once
from .models import CronJobSpec, CronJobState
from .repo.base import BaseJobRepository

HEARTBEAT_JOB_ID = "_heartbeat"

logger = logging.getLogger(__name__)


@dataclass
class _Runtime:
    """Per-job runtime state (concurrency semaphore)."""

    sem: asyncio.Semaphore


class CronJob:
    """A simple registered coroutine job (for built-in tasks)."""

    def __init__(
        self,
        name: str,
        func: Callable[..., Coroutine],
        interval_seconds: int = 3600,
        enabled: bool = True,
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self._task: asyncio.Task | None = None

    async def _run_loop(self):
        """Run the job in a loop."""
        while True:
            try:
                if self.enabled:
                    logger.debug("Running cron job: %s", self.name)
                    await self.func()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Cron job '%s' failed", self.name)
            await asyncio.sleep(self.interval_seconds)


class CronManager:
    """Manages both APScheduler-based persistent jobs and simple registered jobs.

    Used in the FastAPI lifespan to start and stop scheduled tasks like
    paper digest notifications, deadline reminders, and heartbeat.

    When APScheduler is available, persistent jobs use cron triggers.
    Otherwise, falls back to simple asyncio interval loops.
    """

    def __init__(
        self,
        *,
        repo: Optional[BaseJobRepository] = None,
        runner: Any = None,
        channel_manager: Any = None,
        timezone: str = "UTC",
    ):
        self._repo = repo
        self._runner = runner
        self._channel_manager = channel_manager
        self._timezone = timezone

        # Simple registered jobs (backwards compatible)
        self._registered_jobs: dict[str, CronJob] = {}

        # APScheduler state
        self._scheduler: Any = None
        self._executor: Optional[CronExecutor] = None
        if runner and channel_manager:
            self._executor = CronExecutor(
                runner=runner,
                channel_manager=channel_manager,
            )

        self._lock = asyncio.Lock()
        self._states: Dict[str, CronJobState] = {}
        self._rt: Dict[str, _Runtime] = {}
        self._started = False

    def register(
        self,
        name: str,
        func: Callable[..., Coroutine],
        interval_seconds: int = 3600,
        enabled: bool = True,
    ):
        """Register a simple coroutine job."""
        self._registered_jobs[name] = CronJob(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            enabled=enabled,
        )

    async def start(self) -> None:
        """Start all jobs (both registered and persistent)."""
        async with self._lock:
            if self._started:
                return

            # Start simple registered jobs
            for job in self._registered_jobs.values():
                if job.enabled:
                    job._task = asyncio.create_task(job._run_loop())
                    logger.info(
                        "Cron job '%s' started (interval=%ds)",
                        job.name,
                        job.interval_seconds,
                    )

            # Start APScheduler for persistent jobs if repo is available
            if self._repo is not None:
                await self._start_scheduler()

            self._started = True
            logger.info(
                "CronManager started: %d registered, scheduler=%s",
                len(self._registered_jobs),
                "active" if self._scheduler else "disabled",
            )

    async def _start_scheduler(self) -> None:
        """Initialize and start APScheduler with persistent jobs."""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger

            self._scheduler = AsyncIOScheduler(timezone=self._timezone)
            jobs_file = await self._repo.load()

            self._scheduler.start()
            for job in jobs_file.jobs:
                await self._register_or_update(job)

            # Heartbeat: one interval job when enabled
            try:
                from ...config import get_heartbeat_config

                hb = get_heartbeat_config()
                if getattr(hb, "enabled", True):
                    interval_seconds = parse_heartbeat_every(hb.every)
                    self._scheduler.add_job(
                        self._heartbeat_callback,
                        trigger=IntervalTrigger(seconds=interval_seconds),
                        id=HEARTBEAT_JOB_ID,
                        replace_existing=True,
                    )
            except (ImportError, Exception) as e:
                logger.debug("Heartbeat config not available: %s", e)

        except ImportError:
            logger.info(
                "APScheduler not installed; persistent cron jobs disabled. "
                "Install with: pip install apscheduler",
            )

    async def stop(self) -> None:
        """Stop all jobs."""
        async with self._lock:
            if not self._started:
                return

            # Stop simple registered jobs
            for job in self._registered_jobs.values():
                if job._task and not job._task.done():
                    job._task.cancel()
                    try:
                        await job._task
                    except asyncio.CancelledError:
                        pass

            # Stop APScheduler
            if self._scheduler is not None:
                self._scheduler.shutdown(wait=False)

            self._started = False
            logger.info("All cron jobs stopped")

    # ----- Read/state for persistent jobs -----

    async def list_jobs(self) -> list[CronJobSpec]:
        """List all persistent cron jobs."""
        if self._repo is None:
            return []
        return await self._repo.list_jobs()

    async def get_job(self, job_id: str) -> Optional[CronJobSpec]:
        """Get a persistent job by ID."""
        if self._repo is None:
            return None
        return await self._repo.get_job(job_id)

    def get_state(self, job_id: str) -> CronJobState:
        """Get runtime state for a job."""
        return self._states.get(job_id, CronJobState())

    # ----- Write/control for persistent jobs -----

    async def create_or_replace_job(self, spec: CronJobSpec) -> None:
        """Create or update a persistent cron job."""
        if self._repo is None:
            raise RuntimeError(
                "No repository configured; cannot manage persistent jobs",
            )
        async with self._lock:
            await self._repo.upsert_job(spec)
            if self._started and self._scheduler:
                await self._register_or_update(spec)

    async def delete_job(self, job_id: str) -> bool:
        """Delete a persistent cron job."""
        if self._repo is None:
            return False
        async with self._lock:
            if self._started and self._scheduler:
                if self._scheduler.get_job(job_id):
                    self._scheduler.remove_job(job_id)
            self._states.pop(job_id, None)
            self._rt.pop(job_id, None)
            return await self._repo.delete_job(job_id)

    async def pause_job(self, job_id: str) -> None:
        """Pause a persistent cron job."""
        async with self._lock:
            if self._scheduler:
                self._scheduler.pause_job(job_id)

    async def resume_job(self, job_id: str) -> None:
        """Resume a paused persistent cron job."""
        async with self._lock:
            if self._scheduler:
                self._scheduler.resume_job(job_id)

    async def reschedule_heartbeat(self) -> None:
        """Reload heartbeat config and update or remove the heartbeat job."""
        async with self._lock:
            if not self._started or not self._scheduler:
                return
            try:
                from ...config import get_heartbeat_config
                from apscheduler.triggers.interval import IntervalTrigger

                hb = get_heartbeat_config()
                if self._scheduler.get_job(HEARTBEAT_JOB_ID):
                    self._scheduler.remove_job(HEARTBEAT_JOB_ID)
                if getattr(hb, "enabled", True):
                    interval_seconds = parse_heartbeat_every(hb.every)
                    self._scheduler.add_job(
                        self._heartbeat_callback,
                        trigger=IntervalTrigger(seconds=interval_seconds),
                        id=HEARTBEAT_JOB_ID,
                        replace_existing=True,
                    )
                    logger.info(
                        "heartbeat rescheduled: every=%s (interval=%ss)",
                        hb.every,
                        interval_seconds,
                    )
                else:
                    logger.info("heartbeat disabled, job removed")
            except ImportError:
                logger.debug("APScheduler or config not available")

    async def run_job(self, job_id: str) -> None:
        """Trigger a job to run immediately (fire-and-forget).

        Raises KeyError if the job does not exist.
        """
        if self._repo is None:
            raise KeyError(f"Job not found: {job_id}")
        job = await self._repo.get_job(job_id)
        if not job:
            raise KeyError(f"Job not found: {job_id}")
        logger.info(
            "cron run_job (async): job_id=%s channel=%s task_type=%s",
            job_id,
            job.dispatch.channel,
            job.task_type,
        )
        task = asyncio.create_task(
            self._execute_once(job),
            name=f"cron-run-{job_id}",
        )
        task.add_done_callback(lambda t: self._task_done_cb(t, job))

    # ----- Simple registered jobs API (backwards compatible) -----

    def list_registered_jobs(self) -> list[dict[str, Any]]:
        """List all simple registered cron jobs."""
        return [
            {
                "name": job.name,
                "interval_seconds": job.interval_seconds,
                "enabled": job.enabled,
                "running": job._task is not None and not job._task.done(),
            }
            for job in self._registered_jobs.values()
        ]

    def enable_job_by_name(self, name: str):
        """Enable a registered job by name."""
        if name in self._registered_jobs:
            self._registered_jobs[name].enabled = True

    def disable_job_by_name(self, name: str):
        """Disable a registered job by name."""
        if name in self._registered_jobs:
            self._registered_jobs[name].enabled = False

    # ----- Callbacks -----

    def _task_done_cb(self, task: asyncio.Task, job: CronJobSpec) -> None:
        """Suppress and log exceptions from fire-and-forget tasks."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error(
                "cron background task %s failed: %s",
                task.get_name(),
                repr(exc),
            )
            session_id = job.dispatch.target.session_id
            if session_id:
                error_text = f"Cron job [{job.name}] failed: {exc}"
                asyncio.ensure_future(
                    push_store.push(
                        "cron_error",
                        {
                            "session_id": session_id,
                            "text": error_text,
                        },
                    ),
                )

    # ----- Internal -----

    async def _register_or_update(self, spec: CronJobSpec) -> None:
        """Register or update a persistent job in APScheduler."""
        self._rt[spec.id] = _Runtime(
            sem=asyncio.Semaphore(spec.runtime.max_concurrency),
        )

        trigger = self._build_trigger(spec)

        if self._scheduler.get_job(spec.id):
            self._scheduler.remove_job(spec.id)

        self._scheduler.add_job(
            self._scheduled_callback,
            trigger=trigger,
            id=spec.id,
            args=[spec.id],
            misfire_grace_time=spec.runtime.misfire_grace_seconds,
            replace_existing=True,
        )

        if not spec.enabled:
            self._scheduler.pause_job(spec.id)

        aps_job = self._scheduler.get_job(spec.id)
        st = self._states.get(spec.id, CronJobState())
        st.next_run_at = aps_job.next_run_time if aps_job else None
        self._states[spec.id] = st

    def _build_trigger(self, spec: CronJobSpec) -> Any:
        """Build an APScheduler CronTrigger from a CronJobSpec."""
        from apscheduler.triggers.cron import CronTrigger

        parts = [p for p in spec.schedule.cron.split() if p]
        if len(parts) != 5:
            raise ValueError(
                f"cron must have 5 fields, got {len(parts)}: "
                f"{spec.schedule.cron}",
            )
        minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=spec.schedule.timezone,
        )

    async def _scheduled_callback(self, job_id: str) -> None:
        """APScheduler callback for a persistent job."""
        if self._repo is None:
            return
        job = await self._repo.get_job(job_id)
        if not job:
            return

        await self._execute_once(job)

        aps_job = self._scheduler.get_job(job_id)
        st = self._states.get(job_id, CronJobState())
        st.next_run_at = aps_job.next_run_time if aps_job else None
        self._states[job_id] = st

    async def _heartbeat_callback(self) -> None:
        """Run one heartbeat (HEARTBEAT.md as query, optional dispatch)."""
        try:
            await run_heartbeat_once(
                runner=self._runner,
                channel_manager=self._channel_manager,
            )
        except Exception:
            logger.exception("heartbeat run failed")

    async def _execute_once(self, job: CronJobSpec) -> None:
        """Execute a persistent job once with concurrency control."""
        if self._executor is None:
            logger.warning("No executor configured; cannot run job %s", job.id)
            return

        rt = self._rt.get(job.id)
        if not rt:
            rt = _Runtime(sem=asyncio.Semaphore(job.runtime.max_concurrency))
            self._rt[job.id] = rt

        async with rt.sem:
            st = self._states.get(job.id, CronJobState())
            st.last_status = "running"
            self._states[job.id] = st

            try:
                await self._executor.execute(job)
                st.last_status = "success"
                st.last_error = None
                logger.info(
                    "cron _execute_once: job_id=%s status=success",
                    job.id,
                )
            except Exception as e:
                st.last_status = "error"
                st.last_error = repr(e)
                logger.warning(
                    "cron _execute_once: job_id=%s status=error error=%s",
                    job.id,
                    repr(e),
                )
                raise
            finally:
                st.last_run_at = datetime.now(timezone.utc)
                self._states[job.id] = st
