# 快速开始

## 环境要求

- Python 3.10+
- `pip`
- 至少一个可用模型提供商，或可访问的本地模型运行时

## 从当前仓库安装

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
pip install -e .
```

## 初始化工作目录

```bash
researchclaw init --defaults --accept-security
```

默认会创建：

- 工作目录：`~/.researchclaw`
- 密钥目录：`~/.researchclaw.secret`

同时还会写入 Agent 依赖的引导 Markdown 文件，例如 `SOUL.md`、`AGENTS.md`、`PROFILE.md`、`HEARTBEAT.md`。

## 配置模型提供商

```bash
researchclaw models config
```

也可以直接添加：

```bash
researchclaw models add openai --type openai --model gpt-5 --api-key sk-...
```

通过 CLI 添加的第一个 provider 会被自动启用。

## 启动服务

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

浏览器访问 `http://127.0.0.1:8088`。

如果页面提示 `Console not found`，先构建一次前端：

```bash
cd console
npm install
npm run build
```

## 启动后第一步建议

服务启动后，建议先：

- 打开 Console 里的 **Research** 页面
- 创建一个 project
- 查看 workflow、execution health 和 recent blockers
- 再通过 Papers 页面或 API 往这个 project 里灌入文献

## 下一步

- [控制台](./console.md)
- [频道配置](./channels.md)
- [配置与工作目录](./config.md)
- [部署指南](./deployment.md)
