# 配置与工作目录

ResearchClaw 把运行数据和密钥数据分开放。

## 默认路径

- 工作目录：`~/.researchclaw`
- 密钥目录：`~/.researchclaw.secret`

可通过下面两个环境变量覆盖：

- `RESEARCHCLAW_WORKING_DIR`
- `RESEARCHCLAW_SECRET_DIR`
- `RESEARCHCLAW_RESEARCH_DIR`
- `RESEARCHCLAW_RESEARCH_STATE_FILE`

## 工作目录结构

```text
~/.researchclaw/
├── config.json
├── jobs.json
├── chats.json
├── research/
│   └── state.json
├── PROFILE.md
├── SOUL.md
├── AGENTS.md
├── HEARTBEAT.md
├── md_files/
├── sessions/
├── active_skills/
├── customized_skills/
├── papers/
├── references/
├── experiments/
├── memory/
├── custom_channels/
└── researchclaw.log
```

运行过程中还可能生成 `heartbeat.json`、digest、reminder、project research state、agent workspace 等额外产物。

## Research 状态层

Research OS 层把结构化状态单独存放在 chat/session memory 之外：

- 默认目录：`~/.researchclaw/research/`
- 默认文件：`state.json`

这里会保存 projects、workflows、tasks、claims、evidences、notes、experiments、artifacts、drafts。

## 密钥目录结构

```text
~/.researchclaw.secret/
├── envs.json
└── providers.json
```

`providers.json` 是 provider 的规范存储位置，`envs.json` 是持久化环境变量的规范存储位置。

## 引导 Markdown 文件

初始化 / bootstrap 流程要求这些文件存在并完成个性化：

- `SOUL.md`
- `AGENTS.md`
- `PROFILE.md`
- `HEARTBEAT.md`

这些文件对 agent 行为的影响，实际上比很多旧式配置项都更直接。

## `config.json` 示例

```json
{
  "language": "zh",
  "show_tool_details": true,
  "channels": {
    "console": { "enabled": true, "bot_prefix": "[BOT] " },
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
  "agents": {
    "defaults": {
      "agent_id": "main",
      "heartbeat": {
        "enabled": true,
        "every": "1h",
        "target": "last",
        "active_hours": { "start": "08:00", "end": "22:00" }
      }
    },
    "list": [
      { "id": "main", "enabled": true },
      {
        "id": "research",
        "workspace": "agents/research",
        "enabled": true,
        "autostart": true
      }
    ]
  },
  "mcp": {
    "clients": {}
  },
  "automation": {
    "mappings": {}
  }
}
```

## 说明

- 激活 provider 的真实凭证通常来自 `providers.json`，而不是 `config.json`
- `bindings` 也可以放在 `agents.bindings` 下，运行时两种都兼容
- heartbeat 仍兼容旧字段，但推荐使用 `agents.defaults.heartbeat`
- gateway runtime 会在内部写入 `RESEARCHCLAW_RESEARCH_STATE_PATH`，让 research API、skills、runner 共用同一份状态文件
