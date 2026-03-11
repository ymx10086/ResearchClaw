# 部署指南

本文提供一套可直接落地的 ResearchClaw 部署路径。

## 部署模式

- **单机部署（推荐）**：单进程 + 本地持久化 + 反向代理。
- **容器部署**：基于仓库内 `deploy/Dockerfile` 自建镜像。

## 前置条件

- Python 3.10+
- 已配置至少一个模型提供商（`researchclaw models ...`）
- 预留持久化目录（工作目录与密钥目录）

## 最小环境变量

| 变量                            | 是否必需 | 作用                                        |
| ------------------------------- | -------- | ------------------------------------------- |
| `RESEARCHCLAW_WORKING_DIR`      | 是       | 工作数据（`config.json`、聊天、任务、文件） |
| `RESEARCHCLAW_SECRET_DIR`       | 是       | 密钥数据（`envs.json`、`providers.json`）   |
| `RESEARCHCLAW_HOST`             | 建议     | 绑定地址（服务器建议 `0.0.0.0`）            |
| `RESEARCHCLAW_PORT`             | 建议     | 服务端口（默认 `8088`）                     |
| `RESEARCHCLAW_AUTOMATION_TOKEN` | 强烈建议 | 保护 `/api/automation/triggers/*`           |
| `RESEARCHCLAW_CORS_ORIGINS`     | 可选     | 逗号分隔的 CORS 白名单                      |

## 单机部署

### 1) 安装与初始化

```bash
pip install -e ".[dev]"
researchclaw init --defaults --accept-security
researchclaw models config
```

### 2) 设置运行变量并启动

```bash
export RESEARCHCLAW_WORKING_DIR=/data/researchclaw
export RESEARCHCLAW_SECRET_DIR=/data/researchclaw.secret
export RESEARCHCLAW_HOST=0.0.0.0
export RESEARCHCLAW_PORT=8088
export RESEARCHCLAW_AUTOMATION_TOKEN=change-me

researchclaw app --host 0.0.0.0 --port 8088
```

### 3) 启动后检查

```bash
curl -s http://127.0.0.1:8088/api/health
curl -s http://127.0.0.1:8088/api/control/status
```

## Docker 自建镜像部署

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

## 进程托管（systemd 示例）

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

## 反向代理（Nginx 最小示例）

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

## 生产部署检查清单

- 工作目录和密钥目录都做持久化。
- 放在 HTTPS 反向代理后对外服务。
- 尽量通过网络策略限制管理面访问。
- 对外开放自动化触发前设置 `RESEARCHCLAW_AUTOMATION_TOKEN`。
- 监控 `/api/health` 与 `/api/control/status`。

## 常见问题

- **访问 `/` 提示 console not found**：执行 `cd console && npm run build` 构建前端静态资源。
- **模型调用失败**：检查 `researchclaw models list` 和 API Key / Base URL。
- **自动化触发返回 401/503**：
  - 401：请求 token 与服务端不一致。
  - 503：服务端未配置自动化 token。
