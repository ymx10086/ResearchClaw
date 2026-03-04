# 快速开始

## 环境要求

- Python 3.10+
- pip 或 uv

## 安装

### 方式一：pip 安装（推荐）

```bash
pip install researchclaw
```

### 方式二：一键安装脚本（macOS / Linux）

```bash
curl -fsSL https://researchclaw.dev/install.sh | bash
```

### 方式三：Docker

```bash
docker pull researchclaw/researchclaw:latest
docker run -p 8088:8088 -v researchclaw-data:/app/working researchclaw/researchclaw:latest
```

## 初始化

首次使用前，需要初始化工作目录：

```bash
researchclaw init --defaults
```

这会创建默认的配置文件和工作目录。

## 启动

```bash
researchclaw app
```

启动后访问 `http://localhost:8088` 进入控制台。

## 配置 LLM

在控制台中配置你的大语言模型提供商和 API Key：

1. 打开控制台 → 设置
2. 选择模型提供商（OpenAI、Claude、通义千问等）
3. 填入 API Key
4. 保存后即可开始使用

## 下一步

- [频道配置](./channels.md) — 接入钉钉、飞书等 IM 平台
- [Skills](./skills.md) — 了解和扩展科研技能
- [配置与工作目录](./config.md) — 详细的配置说明
