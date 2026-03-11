# 常见问题（FAQ）

<details>
<summary>支持哪些模型提供商？</summary>

支持 OpenAI、Anthropic、DashScope、DeepSeek、Ollama，以及自定义 OpenAI 兼容提供商。

</details>

<details>
<summary>数据默认存储在哪里？</summary>

默认分为两部分：

- 工作数据：`~/.researchclaw`
- 密钥数据（环境变量/模型提供商）：`~/.researchclaw.secret`

</details>

<details>
<summary>可以部署到服务器吗？</summary>

可以。你可以选择：

- 单机部署：`researchclaw app --host 0.0.0.0 --port 8088`
- Docker 自建镜像：使用仓库内 `deploy/Dockerfile`

完整步骤见 [部署指南](./deployment.md)。

</details>

<details>
<summary>自动化触发接口怎么做鉴权？</summary>

在服务端设置 `RESEARCHCLAW_AUTOMATION_TOKEN`，请求侧通过 `Authorization: Bearer <token>`（或 `x-researchclaw-token`）携带相同 token。

</details>

<details>
<summary>为什么访问 `/` 提示 "Console not found"？</summary>

后端可在无前端构建产物时启动。请执行：

```bash
cd console
npm install
npm run build
```

</details>

<details>
<summary>频道配置后无法连通，怎么排查？</summary>

1. 核对平台凭证。
2. 检查机器人权限和回调/webhook 配置。
3. 确认服务网络可访问平台 API。
4. 更新频道凭证后重启服务。

</details>
