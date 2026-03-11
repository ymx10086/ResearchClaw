# 对话命令

ResearchClaw 支持在对话中使用斜杠命令（slash commands）。

## 可用命令

| 命令                    | 说明                 |
| ----------------------- | -------------------- |
| `/new` 或 `/start`      | 新建会话             |
| `/compact`              | 压缩对话记忆         |
| `/clear`                | 清空历史与摘要       |
| `/history`              | 查看会话统计         |
| `/papers`               | 查看最近讨论论文     |
| `/refs`                 | 查看文献库概览       |
| `/skills`               | 查看已启用技能       |
| `/skills debug [query]` | 查看技能路由调试信息 |
| `/compact_str`          | 查看当前压缩摘要     |
| `/daemon status`        | 查看运行状态         |
| `/daemon logs [n]`      | 查看 daemon 日志     |
| `/help`                 | 查看命令帮助         |

## 用法示例

在任意会话中直接输入：

```text
/help
/skills
/skills debug summarize arxiv papers this week
```

## 说明

- 未识别的 slash 命令会回退到自然语言处理。
- `/daemon restart` 在对话路径中受限，建议使用 CLI 执行。
