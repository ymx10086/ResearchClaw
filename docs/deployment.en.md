# Deployment

This page documents the deployment path that matches the current codebase.

## Recommended Shape

Use ResearchClaw as a single FastAPI process with persistent local storage:

- one working directory
- one secret directory
- reverse proxy in front if exposed on a server

## Important Environment Variables

| Variable                        | Recommended | Purpose                                      |
| ------------------------------- | ----------- | -------------------------------------------- |
| `RESEARCHCLAW_WORKING_DIR`      | yes         | runtime data, config, sessions, papers, logs |
| `RESEARCHCLAW_SECRET_DIR`       | yes         | `envs.json` and `providers.json`             |
| `RESEARCHCLAW_HOST`             | yes         | bind host, usually `0.0.0.0` on servers      |
| `RESEARCHCLAW_PORT`             | yes         | service port, default `8088`                 |
| `RESEARCHCLAW_AUTOMATION_TOKEN` | strongly    | protects automation trigger routes           |
| `RESEARCHCLAW_DOCS_ENABLED`     | optional    | enables FastAPI `/docs` and `/redoc`         |
| `RESEARCHCLAW_CORS_ORIGINS`     | optional    | comma-separated CORS allowlist               |

## Single-Machine Deployment

```bash
export RESEARCHCLAW_WORKING_DIR=/data/researchclaw
export RESEARCHCLAW_SECRET_DIR=/data/researchclaw.secret
export RESEARCHCLAW_HOST=0.0.0.0
export RESEARCHCLAW_PORT=8088
export RESEARCHCLAW_AUTOMATION_TOKEN=change-me

researchclaw app --host 0.0.0.0 --port 8088
```

Recommended operational checks:

```bash
curl -s http://127.0.0.1:8088/api/health
curl -s http://127.0.0.1:8088/api/control/status
```

## Docker Self-Build

```bash
docker build -f deploy/Dockerfile -t researchclaw:local .

docker run -d \
  --name researchclaw \
  -p 8088:8088 \
  -e PORT=8088 \
  -e RESEARCHCLAW_WORKING_DIR=/app/working \
  -e RESEARCHCLAW_SECRET_DIR=/app/working.secret \
  -e RESEARCHCLAW_AUTOMATION_TOKEN=change-me \
  -v researchclaw-working:/app/working \
  -v researchclaw-secret:/app/working.secret \
  researchclaw:local
```

## Production Notes

- put the service behind Nginx or Caddy and enable HTTPS
- persist both the working dir and the secret dir
- restrict access to admin/control surfaces where possible
- set the automation token before exposing `/api/automation/*`
- monitor `/api/health` and `/api/control/status`

## Console and Website

- the runtime service serves the **console** from `console/dist`
- the public **website/docs** in `website/` is a separate static site
