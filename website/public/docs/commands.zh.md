# 对话命令

ResearchClaw 会在对话消息里解析 slash commands。

## 主要命令

| 命令                    | 行为                           |
| ----------------------- | ------------------------------ |
| `/new` 或 `/start`      | 开启新的研究会话               |
| `/compact`              | 压缩对话记忆                   |
| `/clear`                | 清空记忆、摘要、讨论论文和笔记 |
| `/history`              | 查看记忆统计                   |
| `/papers`               | 列出最近讨论的论文             |
| `/refs`                 | 汇总当前 BibTeX 文献库         |
| `/skills`               | 列出当前启用的 skills          |
| `/skills debug [query]` | 查看 skill 选择调试细节        |
| `/compact_str`          | 查看当前 compact summary       |
| `/help`                 | 查看命令帮助                   |

## Daemon 风格命令

对话解析器也支持这些 daemon 风格命令：

- `/daemon status`
- `/daemon logs [n]`
- `/daemon reload-config`
- `/daemon version`

同时也支持简写：

- `/status`
- `/logs`
- `/reload-config`
- `/version`

## 关于重启的说明

`/daemon restart` 虽然能被识别，但对话路径并不直接持有 app 生命周期，所以它实际返回的是重启提示，而不是强制重启服务。
