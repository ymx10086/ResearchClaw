# CLI 命令行

ResearchClaw 提供命令行工具用于初始化、启动和管理。

## 安装后可用的命令

```bash
researchclaw <command> [options]
```

## 命令列表

### `init`

初始化工作目录：

```bash
researchclaw init             # 交互式初始化
researchclaw init --defaults  # 使用默认配置初始化
```

### `app`

启动 ResearchClaw 应用：

```bash
researchclaw app                    # 启动
researchclaw app --port 9090        # 指定端口
researchclaw app --host 0.0.0.0     # 指定主机地址
```

### `skills`

管理 Skills：

```bash
researchclaw skills list              # 列出已安装的 Skills
researchclaw skills install <url>     # 从 GitHub 安装 Skill
researchclaw skills uninstall <name>  # 卸载 Skill
```

### `config`

管理配置：

```bash
researchclaw config show              # 显示配置
researchclaw config set <key> <value> # 设置配置项
```

### `version`

显示版本信息：

```bash
researchclaw version
```

## 全局选项

| 选项            | 说明         |
| --------------- | ------------ |
| `--working-dir` | 指定工作目录 |
| `--verbose`     | 显示详细日志 |
| `--help`        | 显示帮助信息 |
