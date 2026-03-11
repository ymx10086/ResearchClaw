# FAQ

<details>
<summary>What model providers are supported?</summary>

ResearchClaw supports OpenAI, Anthropic, DashScope, DeepSeek, Ollama, and custom OpenAI-compatible providers.

</details>

<details>
<summary>Where is my data stored?</summary>

By default:

- Workspace data: `~/.researchclaw`
- Secret data (envs/providers): `~/.researchclaw.secret`

</details>

<details>
<summary>Can I deploy ResearchClaw on a server?</summary>

Yes. Use either:

- single-machine deployment with `researchclaw app --host 0.0.0.0 --port 8088`
- Docker self-build from `deploy/Dockerfile`

See full steps in [Deployment](./deployment.md).

</details>

<details>
<summary>How do I secure automation triggers?</summary>

Set `RESEARCHCLAW_AUTOMATION_TOKEN` on the server and pass the same token via `Authorization: Bearer <token>` (or `x-researchclaw-token`).

</details>

<details>
<summary>Why does `/` show "Console not found"?</summary>

The backend can run without prebuilt frontend assets. Build console assets with:

```bash
cd console
npm install
npm run build
```

</details>

<details>
<summary>Channel integration fails after configuration. What should I check?</summary>

1. Platform credentials are correct.
2. Bot app permissions and callback/webhook URLs are valid.
3. Service network can reach platform APIs.
4. Restart service after channel credential changes.

</details>
