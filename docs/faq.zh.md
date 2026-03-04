# 常见问题 (FAQ)

<details>
<summary>ResearchClaw 支持哪些 LLM 模型？</summary>

支持 OpenAI（GPT-4o、GPT-4 等）、Anthropic（Claude 3.5 等）、通义千问、DeepSeek、Ollama（本地模型）等多种模型提供商。

</details>

<details>
<summary>数据存储在哪里？安全吗？</summary>

所有数据默认存储在本地工作目录（`~/.researchclaw/`）中，不会上传到云端。API Key 等敏感信息加密存储。

</details>

<details>
<summary>如何切换语言？</summary>

ResearchClaw 支持中英文双语。在控制台界面点击语言切换按钮即可切换。CLI 默认使用系统语言。

</details>

<details>
<summary>支持哪些论文数据库？</summary>

目前支持 ArXiv、Semantic Scholar。通过 Skills 系统可以扩展支持更多数据库和论文源。

</details>

<details>
<summary>如何开发自定义 Skill？</summary>

参考 [Skills 文档](./skills.md) 和 [贡献指南](./contributing.md)。每个 Skill 是一个独立的 Python 模块，包含 `skill.json` 元信息文件。

</details>

<details>
<summary>可以在服务器上部署吗？</summary>

可以。推荐使用 Docker 部署：

```bash
docker pull researchclaw/researchclaw:latest
docker run -d -p 8088:8088 -v researchclaw-data:/app/working researchclaw/researchclaw:latest
```

</details>

<details>
<summary>频道配置后无法连接怎么办？</summary>

1. 检查 API Key / Secret 是否正确
2. 确认网络环境可以访问对应平台
3. 查看日志文件排查错误信息
4. 确保已在对应平台创建 Bot 应用并完成权限配置

</details>

<details>
<summary>ResearchClaw 和 CoPaw 是什么关系？</summary>

ResearchClaw 基于 CoPaw 的架构进行了科研领域的定制和优化，专注于论文搜索、文献管理、实验追踪等科研场景。

</details>
