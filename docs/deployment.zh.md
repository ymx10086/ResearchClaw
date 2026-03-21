# 部署指南

本文档按当前代码来写，默认部署形态是单体 FastAPI 服务。

## 推荐部署形态

把 ResearchClaw 当成一个单进程服务来部署：

- 一个 working dir
- 一个 secret dir
- 如果对外提供访问，则在前面挂反向代理

## 关键环境变量

| 变量                            | 建议     | 作用                                   |
| ------------------------------- | -------- | -------------------------------------- |
| `RESEARCHCLAW_WORKING_DIR`      | 是       | 运行数据、配置、sessions、papers、日志 |
| `RESEARCHCLAW_SECRET_DIR`       | 是       | `envs.json` 与 `providers.json`        |
| `RESEARCHCLAW_HOST`             | 是       | 绑定地址，服务器通常设为 `0.0.0.0`     |
| `RESEARCHCLAW_PORT`             | 是       | 服务端口，默认 `8088`                  |
| `RESEARCHCLAW_AUTOMATION_TOKEN` | 强烈建议 | 保护 automation trigger 路由           |
| `RESEARCHCLAW_DOCS_ENABLED`     | 可选     | 是否开启 FastAPI `/docs` 和 `/redoc`   |
| `RESEARCHCLAW_CORS_ORIGINS`     | 可选     | 逗号分隔的 CORS 白名单                 |

## 单机部署

```bash
export RESEARCHCLAW_WORKING_DIR=/data/researchclaw
export RESEARCHCLAW_SECRET_DIR=/data/researchclaw.secret
export RESEARCHCLAW_HOST=0.0.0.0
export RESEARCHCLAW_PORT=8088
export RESEARCHCLAW_AUTOMATION_TOKEN=change-me

researchclaw app --host 0.0.0.0 --port 8088
```

推荐检查：

```bash
curl -s http://127.0.0.1:8088/api/health
curl -s http://127.0.0.1:8088/api/control/status
```

## Docker 自建镜像

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

## 生产注意事项

- 建议放在 Nginx 或 Caddy 后面，并启用 HTTPS
- working dir 和 secret dir 都要持久化
- 尽量限制 admin / control 接口的访问范围
- 对外暴露 `/api/automation/*` 前必须设置 automation token
- 监控 `/api/health` 与 `/api/control/status`

## Console 和 Website 的关系

- 运行时服务托管的是 `console/dist` 中的 **console**
- `website/` 下的 **官网/文档站点** 是独立的静态站点
