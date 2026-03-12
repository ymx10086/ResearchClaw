# Changelog

All notable changes to this project are documented in this file.

## 2026-03-12

### Changed

- Console frontend refresh:
  - added a clearer app shell with topbar context, mobile sidebar toggle, and stronger navigation hierarchy
  - upgraded shared UI primitives (`PageHeader`, metric pills, surface cards) for denser but more consistent control-plane pages
  - added reusable inline notices plus search/filter affordances on key console pages to improve high-frequency operations
  - redesigned chat view with session summary, better empty state prompts, improved message surfaces, and a more deliberate composer area
  - reorganized status/channel/agent-config pages into sectioned dashboards with clearer visual grouping and more polished settings/editing surfaces
  - extended the same visual system to sessions, workspace, cron jobs, models, heartbeat, and skills pages
  - refined global visual tokens for spacing, surfaces, shadows, and gradients while keeping existing information architecture intact

## 2026-03-11

### Added

- Automation trigger APIs:
  - `POST /api/automation/triggers/agent`
  - `POST /api/automation/triggers/wake`
  - `POST /api/automation/hooks/{hook_name}`
  - `GET /api/automation/triggers/runs`
  - `GET /api/automation/triggers/runs/{run_id}`
- Token-based automation ingress auth:
  - `RESEARCHCLAW_AUTOMATION_TOKEN` (env)
  - `config.automation.token` (fallback)
- In-memory automation run history store with bounded retention and status transitions (`queued`, `running`, `succeeded`, `failed`).
- Multi-channel delivery options for automation runs:
  - explicit `dispatches`
  - `fanout_channels` (`["*"]` supported for all active channels)
- Multi-agent runtime routing and observability:
  - config-driven `agents.list`, `agents.defaults`, and routing `bindings`
  - `GET /api/control/agents`
  - per-agent session APIs (`GET/DELETE /api/control/sessions`)
- Channel operations APIs:
  - `GET /api/control/channels/catalog`
  - `GET /api/control/channels/custom`
  - `POST /api/control/channels/custom/install`
  - `DELETE /api/control/channels/custom/{key}`
  - `GET/PUT /api/control/channels/accounts`
  - `GET/PUT /api/control/bindings`
- Runner/model operations APIs:
  - `GET /api/control/usage`
  - `POST /api/control/reload`
  - `POST /api/control/config/apply`

### Changed

- Control-plane observability:
  - `GET /api/control/status` now returns `runtime.runner`, `runtime.channels`, `runtime.cron`, and `runtime.automation` snapshots.
  - Added `GET /api/control/channels/runtime` for queue/worker-level channel runtime stats.
  - Added `GET /api/control/automation/runs` for recent automation run records.
- Channel manager now exposes queue/pending/in-progress/worker runtime metrics via `get_runtime_stats()`.
- Cron manager now exposes runtime counters via `get_runtime_stats()`.
- Console Status page now surfaces:
  - registered channel count
  - queued message backlog
  - in-progress channel keys
  - automation success/failure counters
  - model usage and fallback counters
- Agent runner now supports fallback chains and usage accounting for both non-streaming and streaming chat.
- Channel runtime now supports account alias channels (`channel:account_id`) via `channel_accounts` config.
- Deployment/runtime scripts:
  - `deploy/entrypoint.sh` now starts service with `researchclaw app --host 0.0.0.0 --port ${PORT:-8088}`.
  - `deploy/config/supervisord.conf.template` now uses `researchclaw app` (removed invalid `app start` form).
  - `deploy/Dockerfile` now exposes `8088` to match default app port.
- Docs and README refresh:
  - Added dedicated deployment docs (`website/public/docs/deployment.{en,zh}.md`) and wired them into docs navigation.
  - Updated root `README.md` / `README_zh.md` with practical deployment steps (single-machine, Docker self-build, production checklist).
  - Updated website docs to match current runtime behavior (`config.json`, `models/channels/env` CLI, control-plane and automation observability paths).

### Tests

- Added `tests/test_automation_trigger.py`:
  - dispatch normalization/deduplication
  - fan-out expansion (`*` support)
  - fallback to `last_dispatch`
  - automation run store lifecycle
- Added/updated tests for milestone features:
  - `tests/test_multi_agent_runner.py` (bindings routing, usage aggregation, per-agent sessions)
  - `tests/test_control_router.py` (config apply hooks, usage endpoint, bindings, plugin install/remove)
  - `tests/test_runner_manager_usage.py` (stream fallback + usage stats)
  - `tests/test_channel_accounts_runtime.py` (account alias channel materialization)
