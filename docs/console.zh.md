# 控制台

ResearchClaw 内置 Web 控制台，提供可视化的管理界面。

## 访问

启动 ResearchClaw 后，访问 `http://localhost:8088` 即可进入控制台。

## 功能

### 对话

- 直接与 AI 助手对话
- 查看对话历史
- 多会话管理

### 设置

- 模型提供商配置
- API Key 管理
- 频道开关
- Skills 管理

### 环境变量

- 管理环境变量
- 配置论文源 API Key（如 Semantic Scholar）

### Skills 管理

- 查看已安装的 Skills
- 启用 / 禁用 Skills
- 配置定时任务

## 技术栈

控制台使用 React + TypeScript 构建，通过 WebSocket 与后端实时通信。
