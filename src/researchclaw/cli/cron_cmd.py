"""CLI commands for managing scheduled cron jobs via the HTTP API (/cron)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .http import client, print_json
from ..app.channels.schema import DEFAULT_CHANNEL


def _base_url(ctx: click.Context, base_url: Optional[str]) -> str:
    if base_url:
        return base_url.rstrip("/")
    host = (ctx.obj or {}).get("host", "127.0.0.1")
    port = (ctx.obj or {}).get("port", 8088)
    return f"http://{host}:{port}"


@click.group("cron")
def cron_group() -> None:
    """Manage scheduled cron jobs via the HTTP API (/cron).

    Use list/get/state to inspect jobs; create/delete to add or remove;
    pause/resume to toggle execution; run to trigger a one-off run.
    """


@cron_group.command("list")
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def list_jobs(ctx: click.Context, base_url: Optional[str]) -> None:
    """List all cron jobs."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.get("/cron/jobs")
        r.raise_for_status()
        print_json(r.json())


@cron_group.command("get")
@click.argument("job_id", metavar="JOB_ID")
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def get_job(ctx: click.Context, job_id: str, base_url: Optional[str]) -> None:
    """Fetch a cron job by ID."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.get(f"/cron/jobs/{job_id}")
        if r.status_code == 404:
            raise click.ClickException("Job not found.")
        r.raise_for_status()
        print_json(r.json())


@cron_group.command("state")
@click.argument("job_id", metavar="JOB_ID")
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def job_state(
    ctx: click.Context,
    job_id: str,
    base_url: Optional[str],
) -> None:
    """Get the runtime state of a cron job."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.get(f"/cron/jobs/{job_id}/state")
        if r.status_code == 404:
            raise click.ClickException("Job not found.")
        r.raise_for_status()
        print_json(r.json())


def _build_spec_from_cli(
    task_type: str,
    name: str,
    cron: str,
    channel: str,
    target_user: str,
    target_session: str,
    text: Optional[str],
    timezone: str,
    enabled: bool,
    mode: str,
) -> dict:
    """Build CronJobSpec JSON payload from CLI args."""
    schedule = {"type": "cron", "cron": cron, "timezone": timezone}
    dispatch = {
        "type": "channel",
        "channel": channel,
        "target": {"user_id": target_user, "session_id": target_session},
        "mode": mode,
        "meta": {},
    }
    runtime = {
        "max_concurrency": 1,
        "timeout_seconds": 120,
        "misfire_grace_seconds": 60,
    }
    if task_type == "text":
        if not (text and text.strip()):
            raise click.UsageError(
                "--text is required when task type is 'text'",
            )
        return {
            "id": "",
            "name": name,
            "enabled": enabled,
            "schedule": schedule,
            "task_type": "text",
            "text": text.strip(),
            "dispatch": dispatch,
            "runtime": runtime,
            "meta": {},
        }
    if task_type == "agent":
        if not (text and text.strip()):
            raise click.UsageError(
                "--text is required when task type is 'agent'",
            )
        return {
            "id": "",
            "name": name,
            "enabled": enabled,
            "schedule": schedule,
            "task_type": "agent",
            "request": {
                "input": [
                    {
                        "role": "user",
                        "type": "message",
                        "content": [{"type": "text", "text": text.strip()}],
                    },
                ],
                "session_id": target_session,
                "user_id": "cron",
            },
            "dispatch": dispatch,
            "runtime": runtime,
            "meta": {},
        }
    raise click.UsageError(f"Unsupported task type: {task_type}")


@cron_group.command("create")
@click.option(
    "-f",
    "--file",
    "file_",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="JSON spec file",
)
@click.option(
    "--type",
    "task_type",
    type=click.Choice(["text", "agent"], case_sensitive=False),
    default=None,
    help="Task type",
)
@click.option("--name", default=None, help="Display name")
@click.option("--cron", default=None, help="Cron expression (5 fields)")
@click.option("--channel", default=None, help="Delivery channel")
@click.option("--target-user", default=None, help="Target user_id")
@click.option("--target-session", default=None, help="Target session_id")
@click.option("--text", default=None, help="Content or prompt text")
@click.option("--timezone", default="UTC", help="Timezone")
@click.option(
    "--enabled/--no-enabled",
    default=True,
    help="Create as enabled or disabled",
)
@click.option(
    "--mode",
    type=click.Choice(["stream", "final"], case_sensitive=False),
    default="final",
    help="Delivery mode",
)
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def create_job(
    ctx: click.Context,
    file_: Optional[Path],
    task_type: Optional[str],
    name: Optional[str],
    cron: Optional[str],
    channel: Optional[str],
    target_user: Optional[str],
    target_session: Optional[str],
    text: Optional[str],
    timezone: str,
    enabled: bool,
    mode: str,
    base_url: Optional[str],
) -> None:
    """Create a cron job (inline options or -f JSON file)."""
    base_url = _base_url(ctx, base_url)
    if file_ is not None:
        payload = json.loads(file_.read_text(encoding="utf-8"))
    else:
        for value, label in [
            (task_type, "--type"),
            (name, "--name"),
            (cron, "--cron"),
            (channel, "--channel"),
            (target_user, "--target-user"),
            (target_session, "--target-session"),
        ]:
            if not value or (isinstance(value, str) and not value.strip()):
                raise click.UsageError(
                    f"When creating without -f, {label} is required",
                )
        payload = _build_spec_from_cli(
            task_type=task_type or "agent",
            name=name or "",
            cron=cron or "",
            channel=channel or DEFAULT_CHANNEL,
            target_user=target_user or "",
            target_session=target_session or "",
            text=text,
            timezone=timezone,
            enabled=enabled,
            mode=mode,
        )
    with client(base_url) as c:
        r = c.post("/cron/jobs", json=payload)
        r.raise_for_status()
        print_json(r.json())


@cron_group.command("delete")
@click.argument("job_id", metavar="JOB_ID")
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def delete_job(
    ctx: click.Context,
    job_id: str,
    base_url: Optional[str],
) -> None:
    """Permanently delete a cron job."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.delete(f"/cron/jobs/{job_id}")
        if r.status_code == 404:
            raise click.ClickException("Job not found.")
        r.raise_for_status()
        print_json(r.json())


@cron_group.command("pause")
@click.argument("job_id", metavar="JOB_ID")
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def pause_job(
    ctx: click.Context,
    job_id: str,
    base_url: Optional[str],
) -> None:
    """Pause a cron job."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.post(f"/cron/jobs/{job_id}/pause")
        if r.status_code == 404:
            raise click.ClickException("Job not found.")
        r.raise_for_status()
        print_json(r.json())


@cron_group.command("resume")
@click.argument("job_id", metavar="JOB_ID")
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def resume_job(
    ctx: click.Context,
    job_id: str,
    base_url: Optional[str],
) -> None:
    """Resume a paused cron job."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.post(f"/cron/jobs/{job_id}/resume")
        if r.status_code == 404:
            raise click.ClickException("Job not found.")
        r.raise_for_status()
        print_json(r.json())


@cron_group.command("run")
@click.argument("job_id", metavar="JOB_ID")
@click.option("--base-url", default=None, help="Override the API base URL")
@click.pass_context
def run_job(ctx: click.Context, job_id: str, base_url: Optional[str]) -> None:
    """Trigger a one-off run of a cron job immediately."""
    base_url = _base_url(ctx, base_url)
    with client(base_url) as c:
        r = c.post(f"/cron/jobs/{job_id}/run")
        if r.status_code == 404:
            raise click.ClickException("Job not found.")
        r.raise_for_status()
        print_json(r.json())
