# 控制台

只要 `console/dist` 存在，ResearchClaw 后端就会自动托管运行时控制台。

## 访问方式

启动服务后访问：

```text
http://127.0.0.1:8088
```

## 主要页面

- **Chat**：主对话界面
- **Papers**：论文搜索、本地论文库、BibTeX 引用
- **Research**：project dashboard、workflow、execution health、blocker、claim graph、remediation 操作
- **Channels**：通道目录、启用状态、账号映射、bindings
- **Sessions**：查看和删除路由后的 sessions
- **Cron Jobs**：查看、创建、运行、暂停、恢复、停止任务
- **Heartbeat**：查看 heartbeat 配置和当前状态
- **Status**：运行健康、用量、队列、automation 统计
- **Workspace**：查看工作目录里的关键文件与关系
- **Skills**：列出、启用、禁用、从 hub 安装 skills
- **Agent Config**：查看当前 agent 配置
- **Models**：配置 provider、激活模型、预设模型、本地模型下载
- **Environments**：管理持久化环境变量
- **MCP**：新增、编辑、开关、删除 MCP 客户端

## Research 页面重点

Research 页面是当前 Research OS 层的主要 UI，已经包含：

- project 概览和聚合计数
- workflow 列表与手动推进
- 覆盖 workflow、experiment、bundle、remediation 的 execution health
- recent blockers，以及 task 级 / workflow 级操作
- remediation 详情面板，支持单条和批量 dispatch / execute
- claim graph 查看与证据链检查

## 开发模式

先启动后端，再执行：

```bash
cd console
npm install
npm run dev
```

开发服务器会把 `/api` 代理到 `http://127.0.0.1:8088`。

## 相关 API

- `GET /api/control/status`
- `GET /api/control/usage`
- `GET /api/research/projects/{project_id}/dashboard`
- `POST /api/research/projects/{project_id}/blockers/dispatch`
- `POST /api/research/projects/{project_id}/blockers/execute`
- `POST /api/research/projects/{project_id}/blockers/resume`
- `POST /api/research/workflows/{workflow_id}/execute`
- `GET /api/providers`
- `GET /api/skills`
- `GET /api/mcp`
- `GET /api/workspace`
