# ResearchClaw Gateway Lite

本文档描述的是当前代码里已经存在的 Gateway Lite 形态，而不是一份“未来再做”的重构提案。

## 结论

ResearchClaw 现在已经具备一个清晰的单体内 gateway 边界：

- 仍然是单进程 FastAPI 服务
- 但 runtime access / dispatch / ingress / health 已经被抽到 `app/gateway/*`
- 控制面和运行时共享同一套 runtime snapshot

它不是 OpenClaw 式的独立网关平台，也不打算在当前阶段演化成那样。

## 当前实现

### 1. `_app.py` 负责什么

`src/researchclaw/app/_app.py` 现在主要负责：

- FastAPI app 创建
- lifespan 入口
- router 注册
- console SPA 静态资源托管

真正的 runtime 启停已经不再堆在 `_app.py` 里。

### 2. `gateway/runtime.py` 负责什么

`src/researchclaw/app/gateway/runtime.py` 是当前 gateway-lite 的核心装配层，负责启动并挂到 `app.state` 的组件包括：

- console push store
- automation run store
- multi-agent runner
- chat manager
- channel manager
- research service
- research runtime
- MCP manager / watcher
- cron manager
- config watcher

这里还负责把原始 `config.json` 归一为 channel runtime 可消费的结构。
研究状态文件路径也会在这里写入 `RESEARCHCLAW_RESEARCH_STATE_PATH`，让 runtime、routers、skills 和 agent 工具共享同一份 research state。

### 3. `gateway/dispatch.py` 负责什么

`src/researchclaw/app/gateway/dispatch.py` 提供统一 dispatch target 语义：

- 规范化 channel 名称
- 规范化 `channel + user_id + session_id`
- 去重 dispatch mappings

这让 automation、heartbeat、channel send 等路径可以共享一套目标模型。

### 4. `gateway/ingress.py` 负责什么

`src/researchclaw/app/gateway/ingress.py` 目前比较轻量，主要提供统一的 session id 生成规则，例如：

- `automation:<random>`
- 其他未来 ingress surface 也可以沿用同一前缀模式

### 5. `gateway/health.py` 负责什么

`src/researchclaw/app/gateway/health.py` 现在负责汇总控制面快照，包括：

- runner
- channels
- cron
- heartbeat
- automation
- research
- skills

`/api/control/status` 和状态页都依赖这一层，而不是各处临时拼装。

## 当前已经解决的问题

### Runtime access 有统一入口

通过 `GatewayRuntime` 包装器，主要运行时句柄都统一从 `app.state` 暴露，不再要求 router 直接知道完整启动细节。

### Boot / shutdown 顺序有固定位置

runner、channel manager、cron、MCP watcher、config watcher 的启动顺序已经固定在 `bootstrap_gateway_runtime()` 中，关闭流程则由 `shutdown_gateway_runtime()` 对应回收。

### Control plane 和 runtime 共享一套视图

状态页和 API 现在不再各自拼装一份“差不多”的状态，而是共享 gateway health contract。

### Automation、channels、heartbeat 有了更接近同层的 dispatch 模型

虽然还不是完全统一的 ingress framework，但“投递目标”这件事已经不再是完全分散的 ad-hoc 逻辑。

## 仍然没有做的事

当前 gateway-lite 明确没有覆盖：

- 独立 gateway 进程
- WebSocket method protocol
- 多节点控制面
- OpenAI-compatible gateway façade
- 复杂 auth matrix
- doctor / migration / repair 平台

这些都超出了当前项目阶段的需要。

## 仍然存在的边界问题

虽然 Gateway Lite 已经落地，但还没到“所有入口完全收敛”的程度。

主要还剩：

- 一些用户可见语义仍然分布在 router 层
- channel ingress 适配逻辑仍然主要留在各 channel 实现里
- research workflow 已经进入 gateway runtime，但 project 级 timeline、reporting、deeper execution adapters 仍然主要在 research 层内处理

换句话说，ResearchClaw 已经不只是“先把 runtime 边界抽出来”，而是已经把 research service / runtime 纳入了 gateway-lite 管理；下一步问题不再是“要不要 workflow engine”，而是“怎样把 workflow 能力做得更强、更可审计、更可交付”。

## 后续真正值得做的方向

下一步不应继续抽象 gateway 本身，而应把 gateway-lite 用在更具体的科研闭环上：

- 文献调研流水线入口统一化
- 长任务 checkpoint / resume / project timeline
- artifact schema、result bundle schema 与 evidence routing
- 主动任务、blocker remediation 与失败告警的统一调度

如果这些 workflow 级需求成熟了，再讨论更重的 gateway 演进才有意义。
