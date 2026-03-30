# ResearchClaw 路线图

这份路线图按当前代码状态重写，目标是明确：

- 哪些能力已经落地
- 哪些能力已经进入 Alpha 
- 哪些能力仍然是下一阶段重点

## 当前定位

ResearchClaw 现在更准确的定义是：

- 一个本地优先的 Research OS
- 一个带控制面、消息通道、Automation、Cron、Skills、MCP 的长期运行 Agent 平台
- 一个已经有 project / workflow / claim / evidence / experiment / artifact 主链路的科研工作流系统

一句话目标仍然不变：

**用户在 Console 或 IM 中提出研究任务，系统持续推进，并把过程沉淀成可追踪、可恢复、可复用的科研状态。**

## 当前代码快照

### 已经落地

- [x] Gateway Lite 与控制面
  - `app/gateway/runtime.py`
  - `app/gateway/health.py`
  - `app/gateway/schemas.py`
  - `/api/control/*`
- [x] 多 Agent / channels / providers / skills / MCP
  - multi-agent runner
  - bindings / channel accounts
  - provider fallback chains
  - `SKILL.md` + Skills Hub
  - MCP client 管理
- [x] Research service / runtime 已接入 gateway
  - `research_service`
  - `research_runtime`
  - proactive cycle 与 health snapshot
- [x] Research project 抽象
  - project
  - workflows
  - notes
  - experiments
  - claims
  - artifacts
  - drafts
- [x] Research workflow runtime
  - stage / task / artifact / status / dependency
  - workflow create / pause / resume / cancel / retry
  - session / channel / automation / cron binding
  - 持久化 store
- [x] 结构化 stage worker
  - `literature_search`
  - `paper_reading`
  - `note_synthesis`
  - `hypothesis_queue`
  - `experiment_plan`
  - `experiment_run`
  - `result_analysis`
  - `writing_tasks`
  - `review_and_followup`
- [x] Claim / evidence graph
  - claim / evidence / source / artifact schema
  - paper / note / experiment / citation / generated artifact 关联
  - claim graph 查询 API
- [x] Experiment tracking
  - run schema
  - parameters / inputs / metrics / outputs / notes
  - baseline / ablation / comparison
  - execution binding / event timeline / heartbeat / result ingest
  - artifact contract / result bundle validation
- [x] Structured research notes
  - paper note
  - idea note
  - experiment note
  - writing note
  - decision log
- [x] Proactive automation
  - stale workflow reminder
  - blocked workflow reminder
  - remediation task follow-up
  - paper watch reminder
  - batch dispatch / execute / resume
- [x] Console Research 页面
  - project dashboard
  - execution health
  - recent blockers
  - claim graph
  - remediation detail / batch actions

### 已经具备最小闭环，但还不够强

- [~] 文献调研闭环
  - 已有 literature search / paper reading / notes / claims
  - 还缺高质量去重、打分、evidence matrix、related-work 产物
- [~] 证据链
  - 已有 claim/evidence graph 与查询
  - 还缺更严格的 claim-evidence validator 与冲突分析
- [~] 实验执行
  - 已有 local / command / notebook / external / file-watch execution binding
  - 还缺更强的外部 runner adapter、queue integration、notebook orchestration
- [~] 写作链
  - 已有 writing_tasks / review_and_followup / draft artifact
  - 还缺章节级写作器、reviewer mode、submission packaging
- [~] 长期陪伴
  - 已有 project dashboard、blockers、remediation、proactive cycle
  - 还缺更完整的 project-level timeline、reporting、复盘视图

### 仍然没有做完的关键能力

- [ ] evidence matrix 与跨论文证据聚合
- [ ] 强约束的 claim-evidence validator
- [ ] reproducibility gate
- [ ] submission bundle / camera-ready packaging
- [ ] 更系统的 execution backend catalog
- [ ] 学科/场景化 research agent 编排模板

## 里程碑状态

### M0：运行时基础设施

状态：已完成到可用阶段。

范围：

- gateway-lite 单体边界
- control plane
- channels
- providers / skills / MCP / automation / cron

### M1：Research 状态层

状态：已完成到 Alpha 阶段。

范围：

- project / workflow / task / note / claim / evidence / experiment / artifact schema
- 持久化 store
- API 与 console 基本可视化

### M2：结构化 research workflow

状态：已完成最小闭环。

范围：

- 结构化 stage worker
- workflow 持续推进
- claim/evidence/notes/experiments 回写
- blocker 与 remediation

### M3：实验执行与结果接回

状态：已完成最小主链，继续补强。

已完成：

- execution binding
- external result ingest
- local command/notebook launcher
- result bundle ingest
- contract validation

待补强：

- 更强 execution adapters
- runner preset / environment catalog
- reproducibility 和 replay

### M4：Project 运维与主动推进

状态：已完成 Alpha 主链。

已完成：

- project dashboard
- execution health
- recent blockers
- per-task / per-workflow / per-project dispatch / execute / resume

待补强：

- project timeline
- richer review surfaces
- better reporting/export

### M5：高质量科研交付

状态：未完成。

目标：

- evidence matrix
- stronger validation
- reviewer mode
- submission bundle
- reproducibility checklist

## 下一阶段最重要的事

### 1. 把“可运行闭环”升级成“高质量闭环”

优先补：

- evidence matrix
- claim-evidence conflict detection
- cross-paper synthesis ranking

### 2. 把 execution binding 升级成更真实的执行后端

优先补：

- queue / remote executor adapter
- notebook execution contract
- richer result bundle schema registry

### 3. 把写作与交付真正接上

优先补：

- section-level writing tasks
- reviewer / revision loop
- submission bundle 与 reproducibility gate

### 4. 把 project dashboard 做成长期研究控制面

优先补：

- timeline / weekly summary
- blocker drill-down
- project report / export

## 当前不优先做什么

当前阶段不优先做：

- 独立 gateway 进程
- 多节点控制面
- 通用 OpenAI facade gateway
- 只靠 prompt、没有状态层的“伪 workflow”
- 脱离科研闭环价值的表面 UI 美化
