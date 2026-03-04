# 配置与工作目录

## 工作目录

ResearchClaw 的所有数据和配置文件都存储在工作目录中。默认工作目录为 `~/.researchclaw/`。

### 目录结构

```
~/.researchclaw/
├── config.yaml          # 主配置文件
├── channels.yaml        # 频道配置
├── mcp.yaml             # MCP 配置
├── PROFILE.md           # 助手人设描述
├── skills/              # Skills 文件夹
│   ├── built_in/        # 内置 Skills
│   └── custom/          # 自定义 Skills
├── memory/              # 对话记忆
└── logs/                # 日志文件
```

## 配置文件

### config.yaml

主配置文件，包含 LLM、Memory、Heartbeat 等配置：

```yaml
llm:
  provider: openai
  model: gpt-4o
  api_key: "sk-xxx"

memory:
  compact:
    enabled: true
    max_messages: 50

heartbeat:
  enabled: true
  interval: 60

server:
  host: "0.0.0.0"
  port: 8088
```

### PROFILE.md

定义 AI 助手的人设和行为风格。你可以自定义助手的性格、专长领域和回答风格。

## 环境变量

部分敏感配置可通过环境变量设置：

| 变量名                     | 说明              |
| -------------------------- | ----------------- |
| `RESEARCHCLAW_WORKING_DIR` | 工作目录路径      |
| `OPENAI_API_KEY`           | OpenAI API Key    |
| `ANTHROPIC_API_KEY`        | Anthropic API Key |

## CLI 配置

使用 CLI 命令管理配置：

```bash
researchclaw config show     # 显示当前配置
researchclaw config set key value  # 设置配置项
```
