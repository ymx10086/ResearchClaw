# CLI 命令行

ResearchClaw 提供用于初始化、运行和运维的命令行接口。

## 基本用法

```bash
researchclaw [全局选项] <命令> [子命令/参数]
```

## 全局选项

| 选项         | 说明                                     |
| ------------ | ---------------------------------------- |
| `--host`     | 供 CLI 访问服务 API 时使用的默认主机地址 |
| `--port`     | 供 CLI 访问服务 API 时使用的默认端口     |
| `--version`  | 查看版本                                 |
| `-h, --help` | 查看帮助                                 |

## 核心命令

| 命令        | 作用                         |
| ----------- | ---------------------------- |
| `init`      | 初始化工作目录和引导文件     |
| `app`       | 启动 FastAPI 服务            |
| `models`    | 管理模型提供商和本地模型     |
| `channels`  | 管理频道配置                 |
| `env`       | 管理持久化环境变量           |
| `skills`    | 查看/配置技能启用状态        |
| `cron`      | 通过 HTTP API 管理定时任务   |
| `daemon`    | 运行态管理（状态/重启/日志） |
| `papers`    | 检索与管理论文               |
| `chats`     | 通过 HTTP API 管理会话       |
| `clean`     | 清理工作目录                 |
| `uninstall` | 卸载本地运行环境与命令包装   |

## 常用示例

```bash
researchclaw init --defaults --accept-security
researchclaw app --host 0.0.0.0 --port 8088
researchclaw models list
researchclaw channels list
researchclaw env set OPENAI_API_KEY sk-...
researchclaw cron list
researchclaw daemon status
```

## 说明

- `cron`、`daemon`、`chats` 等命令依赖正在运行的 HTTP 服务，请先启动 `researchclaw app`。
- 与部署相关的启动参数与生产建议，请参考 [部署指南](./deployment.md)。
