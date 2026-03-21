# CLI

ResearchClaw 提供用于初始化、启动运行时和本地运维的命令行工具。

## 全局用法

```bash
researchclaw [--host HOST] [--port PORT] <command> ...
```

## 顶层命令

| 命令        | 作用                               |
| ----------- | ---------------------------------- |
| `init`      | 初始化工作目录和引导 Markdown 文件 |
| `app`       | 启动 FastAPI 服务                  |
| `models`    | 管理 provider 和本地模型           |
| `channels`  | 管理频道配置和自定义频道           |
| `env`       | 管理持久化环境变量                 |
| `skills`    | 列出并配置启用中的 skills          |
| `papers`    | 检索或下载论文                     |
| `cron`      | 通过运行中的 API 管理定时任务      |
| `chats`     | 通过运行中的 API 管理会话          |
| `daemon`    | 查看本地运行信息和日志             |
| `clean`     | 清空 working dir                   |
| `uninstall` | 卸载本地运行环境                   |

## 常用子命令

### `models`

- `researchclaw models list`
- `researchclaw models config`
- `researchclaw models add ...`
- `researchclaw models remove ...`
- `researchclaw models download ...`
- `researchclaw models local`

### `channels`

- `researchclaw channels list`
- `researchclaw channels config`
- `researchclaw channels install <path-or-key>`
- `researchclaw channels remove <key>`

### `skills`

- `researchclaw skills list`
- `researchclaw skills config`

### `env`

- `researchclaw env list`
- `researchclaw env set KEY VALUE`
- `researchclaw env delete KEY`

### `cron`

- `researchclaw cron list`
- `researchclaw cron get JOB_ID`
- `researchclaw cron create ...`
- `researchclaw cron pause JOB_ID`
- `researchclaw cron resume JOB_ID`
- `researchclaw cron run JOB_ID`
- `researchclaw cron state JOB_ID`
- `researchclaw cron delete JOB_ID`

## 说明

- `cron` 和 `chats` 依赖 HTTP 服务处于运行状态
- `models`、`channels`、`skills`、`env`、`papers` 主要是本地操作流程
- `daemon restart` 并不直接持有 app 进程，只会输出重启建议，除非运行时显式绑定了 restart callback
