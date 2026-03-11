# 配置与工作目录

ResearchClaw 将运行数据与密钥数据分目录存储。

## 默认路径

- 工作目录：`~/.researchclaw`
- 密钥目录：`~/.researchclaw.secret`

可通过环境变量覆盖：

- `RESEARCHCLAW_WORKING_DIR`
- `RESEARCHCLAW_SECRET_DIR`

## 工作目录结构

```text
~/.researchclaw/
├── config.json            # 主配置
├── jobs.json              # 持久化 cron 任务
├── chats.json             # 会话历史
├── PROFILE.md             # 用户/研究画像
├── HEARTBEAT.md           # 心跳检查清单
├── active_skills/         # 已启用技能
├── customized_skills/     # 本地自定义技能
├── papers/                # 论文缓存
├── references/            # 文献/BibTeX 数据
├── experiments/           # 实验追踪数据
├── memory/                # 记忆数据
└── researchclaw.log       # 运行日志
```

## 密钥目录结构

```text
~/.researchclaw.secret/
├── envs.json              # 持久化环境变量
└── providers.json         # 模型提供商配置
```

## 关键配置（`config.json`）示例

```json
{
  "language": "zh",
  "show_tool_details": true,
  "channels": {
    "console": { "enabled": true, "bot_prefix": "[BOT] " },
    "dingtalk": { "enabled": false },
    "feishu": { "enabled": false },
    "available": ["console"]
  },
  "channel_accounts": {
    "telegram": {
      "lab": { "enabled": true, "bot_prefix": "[LAB] " }
    }
  },
  "bindings": [
    {
      "agent_id": "research",
      "match": { "channel": "telegram", "account_id": "lab" }
    }
  ],
  "model_fallbacks": [
    { "provider": "anthropic", "model_name": "claude-sonnet-4-20250514" }
  ],
  "agents": {
    "defaults": {
      "heartbeat": {
        "enabled": false,
        "every": "30m",
        "target": "last"
      }
    }
  },
  "mcp": {
    "clients": {}
  }
}
```

## 常用配置命令

```bash
researchclaw init
researchclaw channels config
researchclaw models config
researchclaw env list
researchclaw env set OPENAI_API_KEY sk-...
```

## 重要高级字段

- `channel_accounts`：频道账号级覆盖配置；每个账号会映射为 `channel:account_id`。
- `bindings`：多 Agent 路由规则，可按 channel/account/user/session 进行分流。
- `model_fallbacks`：主模型失败时的备用 provider/model 链。

## 与部署相关的环境变量

| 变量                            | 说明                            |
| ------------------------------- | ------------------------------- |
| `RESEARCHCLAW_HOST`             | `researchclaw app` 默认绑定地址 |
| `RESEARCHCLAW_PORT`             | `researchclaw app` 默认端口     |
| `RESEARCHCLAW_AUTOMATION_TOKEN` | 自动化触发 API 鉴权 token       |
| `RESEARCHCLAW_CORS_ORIGINS`     | CORS 白名单                     |
| `RESEARCHCLAW_DOCS_ENABLED`     | 是否启用 FastAPI `/docs`        |
| `RESEARCHCLAW_LOG_LEVEL`        | 运行日志级别                    |

生产部署请参考 [部署指南](./deployment.md)。
