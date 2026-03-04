# FAQ

<details>
<summary>What LLM models does ResearchClaw support?</summary>

Supports OpenAI (GPT-4o, GPT-4, etc.), Anthropic (Claude 3.5, etc.), Qwen, DeepSeek, Ollama (local models), and more.

</details>

<details>
<summary>Where is data stored? Is it secure?</summary>

All data is stored locally in the working directory (`~/.researchclaw/`) by default and is never uploaded to the cloud. Sensitive data like API keys is encrypted.

</details>

<details>
<summary>How do I switch languages?</summary>

ResearchClaw supports both Chinese and English. Click the language toggle in the console UI. The CLI defaults to the system language.

</details>

<details>
<summary>Which paper databases are supported?</summary>

Currently supports ArXiv and Semantic Scholar. More databases and paper sources can be added through the Skills system.

</details>

<details>
<summary>How do I develop a custom Skill?</summary>

See the [Skills documentation](./skills.md) and [Contributing guide](./contributing.md). Each Skill is an independent Python module with a `skill.json` metadata file.

</details>

<details>
<summary>Can I deploy on a server?</summary>

Yes. Docker deployment is recommended:

```bash
docker pull researchclaw/researchclaw:latest
docker run -d -p 8088:8088 -v researchclaw-data:/app/working researchclaw/researchclaw:latest
```

</details>

<details>
<summary>Channel won't connect after configuration?</summary>

1. Check that API Key / Secret are correct
2. Verify network access to the platform
3. Check log files for error messages
4. Ensure a Bot application has been created on the platform with proper permissions

</details>

<details>
<summary>What is the relationship between ResearchClaw and CoPaw?</summary>

ResearchClaw is built on CoPaw's architecture, customized and optimized for research scenarios including paper search, reference management, and experiment tracking.

</details>
