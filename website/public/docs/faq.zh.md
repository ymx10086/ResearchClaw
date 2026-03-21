# 常见问题

下面的回答按当前仓库代码状态编写。

### 现在已经比较接近可用产品的部分是什么？

当前最成熟的是运行时平台层和有状态的 research foundation：

- app 启停与控制面 API
- channels、providers、skills、MCP、automation、console
- project / workflow / task 状态层
- claim / evidence graph
- experiment tracking、result bundle ingest、blocker remediation

真正还没做完的是更高层的科研质量问题：evidence matrix 打分、更严格的 claim validator、更丰富的外部执行适配器，以及 submission packaging。

### 当前支持哪些 provider？

代码里支持的 provider type 有：`openai`、`anthropic`、`gemini`、`ollama`、`dashscope`、`deepseek`、`minimax`、`other`、`custom`。

### 当前内置哪些频道？

`console`、`telegram`、`discord`、`dingtalk`、`feishu`、`imessage`、`qq`、`voice`。

### 数据默认存在哪里？

- 工作数据：`~/.researchclaw`
- 密钥数据：`~/.researchclaw.secret`

其中 `envs.json` 和 `providers.json` 都在 secret dir 下。

research workflow 的状态默认在 `~/.researchclaw/research/state.json`，除非你覆盖了 research path。

### 为什么访问 `/` 会提示 `Console not found`？

后端可以在没有预构建 console 的情况下启动。先构建一次前端：

```bash
cd console
npm install
npm run build
```

### automation trigger 怎么做鉴权？

在服务端设置 `RESEARCHCLAW_AUTOMATION_TOKEN`。请求方需要通过 `Authorization: Bearer <token>`、`x-researchclaw-token` 或 `x-researchclaw-automation-token` 发送同一个 token。

### 为什么新 clone 下来的仓库直接跑 `pytest` 可能失败？

如果还没做 editable install，Python 可能找不到 `researchclaw` 包。可以执行：

```bash
pip install -e ".[dev]"
```

或者：

```bash
PYTHONPATH=src pytest -q
```

### Console 里已经有研究工作流控制面了吗？

有。当前 Console 已经有专门的 Research 页面，包含：

- project dashboard
- workflow 执行
- execution health
- recent blockers
- remediation drill-down 和 batch actions
