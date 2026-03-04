"""Cron job models — schedules, dispatch targets, job specs, and state.

Provides Pydantic models for defining and persisting cron jobs with
research-specific extensions (deadline tracking, paper digests).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from ..channels.schema import DEFAULT_CHANNEL


class ScheduleSpec(BaseModel):
    """Cron schedule specification with 5-field cron expression."""

    type: Literal["cron"] = "cron"
    cron: str = Field(...)
    timezone: str = "UTC"

    @field_validator("cron")
    @classmethod
    def normalize_cron_5_fields(cls, v: str) -> str:
        """Normalize cron expression to 5 fields (min hour dom month dow)."""
        parts = [p for p in v.split() if p]
        if len(parts) == 5:
            return " ".join(parts)
        if len(parts) == 4:
            # treat as: hour dom month dow
            hour, dom, month, dow = parts
            return f"0 {hour} {dom} {month} {dow}"
        if len(parts) == 3:
            # treat as: dom month dow
            dom, month, dow = parts
            return f"0 0 {dom} {month} {dow}"
        raise ValueError(
            "cron must have 5 fields "
            "(or 4/3 fields that can be normalized); seconds not supported.",
        )


class DispatchTarget(BaseModel):
    """Target user/session for dispatching cron job results."""

    user_id: str
    session_id: str


class DispatchSpec(BaseModel):
    """Dispatch configuration for a cron job."""

    type: Literal["channel"] = "channel"
    channel: str = Field(default=DEFAULT_CHANNEL)
    target: DispatchTarget
    mode: Literal["stream", "final"] = Field(default="stream")
    meta: Dict[str, Any] = Field(default_factory=dict)


class JobRuntimeSpec(BaseModel):
    """Runtime constraints for a cron job."""

    max_concurrency: int = Field(default=1, ge=1)
    timeout_seconds: int = Field(default=120, ge=1)
    misfire_grace_seconds: int = Field(default=60, ge=0)


class CronJobRequest(BaseModel):
    """Passthrough payload to runner.stream_query(request=...).

    Kept permissive to allow arbitrary input formats.
    """

    model_config = ConfigDict(extra="allow")

    input: Any
    session_id: Optional[str] = None
    user_id: Optional[str] = None


TaskType = Literal["text", "agent"]


class CronJobSpec(BaseModel):
    """Full specification for a cron job.

    Supports two task types:
    - text: Send fixed text message to a channel
    - agent: Run the agent with a prompt and dispatch the response
    """

    id: str
    name: str
    enabled: bool = True

    schedule: ScheduleSpec
    task_type: TaskType = "agent"
    text: Optional[str] = None
    request: Optional[CronJobRequest] = None
    dispatch: DispatchSpec

    runtime: JobRuntimeSpec = Field(default_factory=JobRuntimeSpec)
    meta: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_task_type_fields(self) -> "CronJobSpec":
        if self.task_type == "text":
            if not (self.text and self.text.strip()):
                raise ValueError("task_type is text but text is empty")
        elif self.task_type == "agent":
            if self.request is None:
                raise ValueError("task_type is agent but request is missing")
            target = self.dispatch.target
            self.request = self.request.model_copy(
                update={
                    "user_id": target.user_id,
                    "session_id": target.session_id,
                },
            )
        return self


class JobsFile(BaseModel):
    """Jobs registry file for JSON repository."""

    version: int = 1
    jobs: list[CronJobSpec] = Field(default_factory=list)


class CronJobState(BaseModel):
    """Runtime state tracking for a cron job."""

    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_status: Optional[
        Literal["success", "error", "running", "skipped"]
    ] = None
    last_error: Optional[str] = None


class CronJobView(BaseModel):
    """Full view of a cron job: spec + runtime state."""

    spec: CronJobSpec
    state: CronJobState = Field(default_factory=CronJobState)
