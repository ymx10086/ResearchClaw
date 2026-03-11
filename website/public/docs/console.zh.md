# 控制台

ResearchClaw 内置 Web 控制台，用于日常使用与运维观测。

## 访问

服务启动后访问 `http://<host>:<port>`（默认 `http://127.0.0.1:8088`）。

## 核心页面

### 对话

- 与 Scholar 助手对话
- 多会话管理
- 查看历史消息

### 设置

- 配置模型提供商与模型
- 管理频道开关与凭证
- 管理持久化环境变量
- 管理技能（启用/禁用）

### 状态页 / 控制面

- 运行健康状态与 uptime
- 模型用量指标（请求数/成功率/回退次数/token 估算）
- 频道队列/worker 运行指标
- cron 运行指标
- 自动化任务统计（queued/running/succeeded/failed）
- Agent 列表与会话可观测

## 相关 API

- `GET /api/control/status`
- `GET /api/control/usage`
- `GET /api/control/channels/runtime`
- `GET /api/control/automation/runs`
- `GET /api/control/agents`
- `GET /api/control/sessions`
- `POST /api/control/reload`

生产部署访问建议请参考 [部署指南](./deployment.md)。
