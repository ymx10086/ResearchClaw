# Deployment

This page explains a practical deployment path for ResearchClaw with clear defaults.

## Deployment Modes

- **Single machine (recommended)**: one process, local disk persistence, reverse proxy in front.
- **Containerized**: build your own image from `deploy/Dockerfile`.

## Prerequisites

- Python 3.10+
- A configured model provider (`researchclaw models ...`)
- Persistent disk paths for workspace and secrets

## Environment Variables (Minimum)

| Variable                        | Required             | Purpose                                            |
| ------------------------------- | -------------------- | -------------------------------------------------- |
| `RESEARCHCLAW_WORKING_DIR`      | Yes                  | Workspace data (`config.json`, chats, jobs, files) |
| `RESEARCHCLAW_SECRET_DIR`       | Yes                  | Secrets store (`envs.json`, `providers.json`)      |
| `RESEARCHCLAW_HOST`             | Recommended          | Bind host (set `0.0.0.0` on servers)               |
| `RESEARCHCLAW_PORT`             | Recommended          | Service port (default `8088`)                      |
| `RESEARCHCLAW_AUTOMATION_TOKEN` | Strongly recommended | Protect `/api/automation/triggers/*`               |
| `RESEARCHCLAW_CORS_ORIGINS`     | Optional             | Comma-separated CORS origins                       |

## Single-Machine Deployment

### 1) Install and initialize

```bash
pip install -e ".[dev]"
researchclaw init --defaults --accept-security
researchclaw models config
```

### 2) Set runtime env and start service

```bash
export RESEARCHCLAW_WORKING_DIR=/data/researchclaw
export RESEARCHCLAW_SECRET_DIR=/data/researchclaw.secret
export RESEARCHCLAW_HOST=0.0.0.0
export RESEARCHCLAW_PORT=8088
export RESEARCHCLAW_AUTOMATION_TOKEN=change-me

researchclaw app --host 0.0.0.0 --port 8088
```

### 3) Verify service

```bash
curl -s http://127.0.0.1:8088/api/health
curl -s http://127.0.0.1:8088/api/control/status
```

## Docker Deployment (Self-Build)

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

## Run as a Service (systemd example)

```ini
[Unit]
Description=ResearchClaw
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/researchclaw
Environment=RESEARCHCLAW_WORKING_DIR=/data/researchclaw
Environment=RESEARCHCLAW_SECRET_DIR=/data/researchclaw.secret
Environment=RESEARCHCLAW_AUTOMATION_TOKEN=change-me
ExecStart=/usr/local/bin/researchclaw app --host 0.0.0.0 --port 8088
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## Reverse Proxy (Nginx minimal)

```nginx
server {
  listen 443 ssl;
  server_name rc.example.com;

  location / {
    proxy_pass http://127.0.0.1:8088;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

## Production Checklist

- Persist both workspace and secret directories.
- Put the service behind HTTPS.
- Restrict management surface by network policy whenever possible.
- Set `RESEARCHCLAW_AUTOMATION_TOKEN` before exposing automation trigger APIs.
- Monitor `/api/health` and `/api/control/status`.

## Troubleshooting

- **`/` shows console not found**: build frontend assets with `cd console && npm run build`.
- **Model calls fail**: check `researchclaw models list` and API key/base URL.
- **Automation trigger returns 401/503**:
  - 401: request token mismatch.
  - 503: automation token not configured.
