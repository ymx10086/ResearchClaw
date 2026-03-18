# ResearchClaw 路线图

## 定位

ResearchClaw 不是“只在终端里跑命令”的工具集合，而是：

- 一个可被 IM 控制的个人科研 Agent 工作台
- 交互入口以 IM/Console 为主，CLI 负责初始化、配置、运维
- 参考 CoPaw/OpenClaw 的运行范式：多通道接入 + 常驻运行 + 定时任务 + 可扩展 Skills/MCP

一句话目标：
**用户在 IM 中下达任务，Agent 持续推进文献调研、问题提出、实验执行、写作产出，并把关键进展主动推送回来。**

## 北极星场景

用户在飞书发送：

1. “帮我调研 diffusion model 在医学分割的最新进展，给出空白点”
2. “基于空白点给 3 个可验证假设，选风险最低的一个”
3. “开始实验，今晚给我 baseline + ablation 结果”
4. “按论文结构起草方法和实验章节，附引用”

Agent 能在同一会话持续推进，并通过 IM/Console 回传阶段性产物与告警。

## 目标交互模型（IM 主、CLI 辅）

### IM 层（主入口）

- 自然语言任务驱动
- 轻量控制指令（示例）：
  - `/plan`
  - `/status`
  - `/pause`
  - `/resume`
  - `/deliver`
  - `/evidence`

### CLI 层（控制面）

- 初始化与配置：`researchclaw init`, `researchclaw channels config`
- 运维与诊断：`researchclaw daemon`, `researchclaw cron`, `researchclaw channels list`
- 本地开发与调试：`researchclaw app` + console dev server

## 架构路线（对齐现有基础）

### A. Channel Runtime（多通道入口）

- 统一会话语义：不同渠道消息归一到统一 request/event
- 队列与去重：保证同一会话不会重复响应、乱序响应
- 主动推送能力：实验完成、心跳摘要、失败告警可回推到上次活跃渠道

### B. Control Plane（运行控制面）

- 常驻状态可观测：runner/channels/cron/mcp 健康状态
- 配置热更新：模型、通道、定时任务变更尽量无感生效
- 故障恢复：重启后会话与关键任务状态可恢复
- Gateway Lite：把 runtime / ingress / dispatch / health 边界从 `_app.py` 和 routers 中抽出，但保持单体部署

### F. Gateway Lite（单体内网关边界）

- 统一 runtime access：runner / channels / cron / mcp / automation store 通过统一 gateway runtime 暴露
- 统一 ingress 语义：automation trigger、channel ingress、manual run、future webhook 使用一致的入口模型
- 统一 dispatch 语义：channel / user / session / agent 路由收敛到同层
- 统一 health contract：控制面和观测页共享一套 runtime snapshot
- 保持单体：当前不拆独立 gateway 进程，不引入额外部署复杂度

### C. Research Workflow Engine（科研流程引擎）

- 从“单轮问答”升级为“阶段化科研工作流”
- 阶段：
  - 文献检索与筛选
  - 研究问题与假设生成
  - 实验计划与执行
  - 统计分析与结论校验
  - 论文草稿与审稿修订

### D. Evidence & Memory（证据与记忆层）

- 产物结构化落盘（project/question/hypothesis/experiment/result/draft）
- claim-evidence 绑定（每个结论可追溯到实验与引用）
- 长会话压缩与跨会话记忆，避免上下文漂移

### E. Scheduler & Autopilot（主动推进）

- heartbeat 驱动“低频自检 + 高价值提醒”
- cron 驱动定时任务（论文摘要、实验巡检、截止日提醒）
- 支持“被动响应 + 主动推进”双模式

## 里程碑与验收标准（按 IM Agent 目标重排）

### M1（2026-03-07 ~ 2026-04-15）：IM 基础设施稳态
- [ ] 通道会话统一协议（session/user/message/event）
- [ ] 多通道稳定性增强（去重、合并、限流、错误隔离）
- [ ] 控制面状态页与诊断命令完善
- 验收标准
- [ ] 至少 2 个 IM 渠道 + Console 连续稳定运行 7 天
- [ ] 消息重复响应率 < 1%，关键错误可观测

### M2（2026-04-16 ~ 2026-06-01）：文献调研工作流（IM 内闭环）
- [ ] 文献检索、去重、打分、证据提取流水线
- [ ] 产出 evidence matrix 与 related-work 草案
- [ ] IM 中支持“继续追问 + 缩小范围 + 一键导出”
- 验收标准
- [ ] 用户可仅在 IM 完成从主题到文献综述草稿

### M3（2026-06-02 ~ 2026-08-01）：问题提出到实验编排
- [ ] gap/question/hypothesis 结构化生成
- [ ] 实验计划、运行、日志、元数据自动归档
- [ ] 基线对比与消融流程标准化
- 验收标准
- [ ] 在 IM 发起实验后，Agent 可异步执行并主动回传结果

### M4（2026-08-02 ~ 2026-10-01）：写作与证据一致性
- [ ] 按论文结构生成方法/实验/结论草稿
- [ ] claim-evidence 一致性检查器
- [ ] 审稿人模式（质疑点、补实验建议、过度结论检测）
- 验收标准
- [ ] 生成稿件中核心结论可追溯到具体实验与引用

### M5（2026-10-02 ~ 2026-12-01）：全流程自动化与提交准备
- [ ] 提交前检查清单（引用、证据、复现、风险）
- [ ] 复现材料打包（配置、seed、环境、日志、脚本）
- [ ] 一键“从任务到 submission bundle”编排
- 验收标准
- [ ] 用户在 IM 发出高层目标后，系统可完成端到端交付并回传包

## Epic 拆解（建议创建子 Issue）

- [ ] EPIC: IM-native session protocol and channel reliability
- [ ] EPIC: Gateway Lite runtime/ingress/dispatch boundary
- [ ] EPIC: Research workflow state machine and artifact schema
- [ ] EPIC: Literature triage and evidence matrix pipeline
- [ ] EPIC: Hypothesis generation and experiment orchestration
- [ ] EPIC: Claim-evidence validator and reviewer mode
- [ ] EPIC: Scheduler/autopilot for proactive research progress
- [ ] EPIC: Submission packaging and reproducibility gate

## 建议标签与里程碑

- Labels: `roadmap`, `epic`, `im-first`, `channels`, `runtime`, `research-workflow`, `experiments`, `writing`, `reproducibility`
- Milestones: `M1-IM-Runtime`, `M2-Survey`, `M3-Experiment`, `M4-Writing`, `M5-Submission`

## KPI（按 IM Agent 形态）

- IM 端到端任务完成率（topic -> draft/package）>= 70%
- 主动推送成功率 >= 95%
- 实验可重放成功率 >= 90%
- 关键结论证据可回溯率 >= 95%
- 人工接管率（需手动修复流程）逐季下降

## 风险与缓解

- [ ] 多通道行为不一致 -> 统一事件协议 + 渠道适配层测试矩阵
- [ ] 长任务中断/漂移 -> 工作流状态机 + checkpoint + resume
- [ ] 结论缺证据 -> 强制 claim-evidence gate
- [ ] 主动任务扰民 -> 可配置静默时段、优先级和通知策略
- [ ] 安全边界不足 -> 工具权限分级、敏感操作确认、审计日志

## 未来 2 周优先项（立即可执行）

- [ ] 完成“IM 主入口、CLI 控制面”的文档与命令语义对齐
- [ ] 落地 Gateway Lite Phase 1：新增 `app/gateway/*`，把 runtime boot/shutdown 从 `_app.py` 抽出
- [ ] 定义科研流程状态机与 artifact schema（最小可用版本）
- [ ] 打通“文献调研 -> evidence matrix -> IM 回传”第一条闭环
- [ ] 为通道可靠性建立回归用例（去重、并发、恢复）

加油
