# 快速开始

## 环境要求

- Python 3.10+
- pip 或 uv

## 安装

### 方式一：从源码安装（适合贡献者，推荐）

```bash
git clone https://github.com/ymx10086/ResearchClaw.git
cd ResearchClaw
pip install -e ".[dev]"
```

### 方式二：从发布包安装

```bash
pip install researchclaw
```

## 初始化工作目录

```bash
researchclaw init --defaults --accept-security
```

默认会创建 `~/.researchclaw`。

## 配置模型提供商

```bash
researchclaw models config
# 或直接添加：
researchclaw models add openai --type openai --model gpt-4o --api-key sk-...
```

## 启动服务

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

访问 `http://127.0.0.1:8088`。

## 部署下一步

如需服务器部署（Docker / systemd / Nginx），请看 [部署指南](./deployment.md)。

## 下一步

- [控制台](./console.md) — UI 能力与操作入口
- [频道配置](./channels.md) — 多渠道接入
- [配置与工作目录](./config.md) — 文件、环境变量与持久化
