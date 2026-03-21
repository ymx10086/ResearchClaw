import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type Locale = "zh" | "en";

const STORAGE_KEY = "researchclaw.console.locale";

const EN_DICT: Record<string, string> = {
  "让重复退场，让创造登场。": "Retire repetition. Let creation take the stage.",
  研究: "Research",
  控制: "Control",
  智能体: "Agent",
  设置: "Settings",
  "AI 对话": "AI Chat",
  研究项目: "Research Projects",
  论文检索: "Paper Search",
  频道: "Channels",
  会话: "Sessions",
  定时任务: "Scheduled Jobs",
  心跳: "Heartbeat",
  系统状态: "System Status",
  工作区: "Workspace",
  技能: "Skills",
  "Agent 配置": "Agent Config",
  模型: "Models",
  环境变量: "Environment Variables",
  "ResearchClaw 运行中": "ResearchClaw Running",
  刷新: "Refresh",
  语言: "Language",
  中文: "Chinese",
  切换语言: "Switch language",
  打开导航: "Open navigation",
  关闭导航: "Close navigation",
  加载: "Load",
  新建任务: "New Job",
  新对话: "New Chat",
  继续对话: "Continue Chat",
  查看: "View",
  删除: "Delete",
  编辑: "Edit",
  保存: "Save",
  取消: "Cancel",
  重置: "Reset",
  停止: "Stop",
  发送: "Send",
  "运行中...": "Running...",
  推理中: "Reasoning",
  可交互: "Interactive",
  "保存中...": "Saving...",
  "删除中...": "Deleting...",
  "应用中...": "Applying...",
  "检索中...": "Searching...",
  "加载中...": "Loading...",
  已启用: "Enabled",
  已禁用: "Disabled",
  已暂停: "Paused",
  启用: "Enable",
  暂停: "Pause",
  启用状态: "Status",
  任务名称: "Job Name",
  任务类型: "Task Type",
  时区: "Timezone",
  通道: "Channel",
  目标: "Target",
  "目标 User ID": "Target User ID",
  "目标 Session ID": "Target Session ID",
  发送模式: "Dispatch Mode",
  并发上限: "Max Concurrency",
  超时秒数: "Timeout (seconds)",
  错过触发宽限秒数: "Misfire Grace (seconds)",
  文本内容: "Text Content",
  "Agent 提示词": "Agent Prompt",
  "Cron 表达式": "Cron Expression",
  "Cron 表达式不能为空": "Cron expression cannot be empty",
  任务名称不能为空: "Task name cannot be empty",
  文本内容不能为空: "Text content cannot be empty",
  "Agent 提示词不能为空": "Agent prompt cannot be empty",
  "确认删除定时任务「{name}」吗？":
    'Are you sure you want to delete scheduled job "{name}"?',
  '确定删除供应商 "{name}"？':
    'Are you sure you want to delete provider "{name}"?',
  "通道 (默认 console)": "Channel (default: console)",
  马上运行: "Run Now",
  编辑定时任务: "Edit Job",
  新建定时任务: "New Job",
  加载定时任务: "Loading Jobs",
  暂无定时任务: "No Scheduled Jobs",
  刷新任务: "Refresh Jobs",
  点击刷新加载频道: "Click Refresh to Load Channels",
  频道管理: "Channel Management",
  刷新频道: "Refresh Channels",
  会话管理: "Session Management",
  刷新会话: "Refresh Sessions",
  会话详情: "Session Detail",
  开始一段研究对话: "Start a Research Conversation",
  暂无历史会话: "No Chat History",
  "当前会话: ": "Current Session: ",
  历史会话: "History",
  当前模式: "Mode",
  最近更新: "Updated",
  研究线程: "Research Threads",
  未创建: "Not Created",
  思考过程: "Reasoning",
  "正在思考...": "Thinking...",
  加载工作区信息: "Loading Workspace",
  工作区文件: "Workspace Files",
  刷新工作区: "Refresh Workspace",
  关键文件: "Key Files",
  必需: "Required",
  请选择文件: "Please select a file",
  "加载文件中...": "Loading file...",
  对话: "Chat",
  趋势梳理: "Trend Scan",
  实验计划: "Experiment Plan",
  配置: "Config",
  "对话 / 技能 / 定时 / 心跳 关系":
    "Chat / Skills / Schedules / Heartbeat Relations",
  刷新状态: "Refresh Status",
  "API 健康": "API Health",
  正常: "Healthy",
  运行状态: "Runtime",
  运行中: "Running",
  已停止: "Stopped",
  可用工具: "Available Tools",
  激活技能: "Active Skills",
  关闭: "Off",
  运行模式: "Run Mode",
  运行时长: "Uptime",
  加载技能列表: "Loading Skills",
  技能管理: "Skill Management",
  刷新技能: "Refresh Skills",
  加载环境变量: "Loading Environment Variables",
  "检索 ArXiv": "Search ArXiv",
  未找到相关论文: "No relevant papers found",
  搜索学术论文: "Search Academic Papers",
  当前筛选条件下没有匹配频道: "No channels match the current filters",
  当前筛选条件下没有匹配目录项: "No catalog entries match the current filters",
  当前筛选条件下没有匹配插件: "No plugins match the current filters",
  当前筛选条件下没有匹配文件: "No files match the current filters",
  当前筛选条件下没有匹配技能: "No skills match the current filters",
  当前筛选条件下没有匹配任务: "No jobs match the current filters",
  当前筛选条件下没有匹配供应商: "No providers match the current filters",
  当前筛选条件下没有匹配会话: "No sessions match the current filters",
  "当前筛选结果 {filtered} / {total}": "Filtered results {filtered} / {total}",
  会话数: "Sessions",
  "可选 Agent": "Available Agents",
  "查看和管理所有 Agent 交互会话":
    "View and manage all agent interaction sessions",
  "确认删除会话 {id} 吗？": 'Are you sure you want to delete session "{id}"?',
  "按 Agent 查看历史会话，快速恢复研究线程并继续推进当前任务。":
    "Browse session history by agent, resume research threads quickly, and continue the current task.",
  "可以直接查看详情、继续对话，或者按 Agent 范围清理历史会话。":
    "View details, continue the conversation, or clear session history by agent.",
  "{count} 条": "{count} messages",
  "{count} 条消息": "{count} messages",
  "MCP 客户端": "MCP Clients",
  新增客户端: "New Client",
  "加载 MCP 客户端": "Loading MCP Clients",
  添加新客户端: "Add New Client",
  新增供应商: "Add Provider",
  供应商类型: "Provider Type",
  模型名称: "Model Name",
  "应用到 Agent（热重载）": "Apply to Agent (hot reload)",
  应用: "Apply",
  保存设置: "Save Settings",
  "模型 & 供应商": "Models & Providers",
  加载供应商配置: "Loading Provider Config",
  暂无供应商: "No Providers",
  "加载 Agent 配置": "Loading Agent Config",
  加载配置: "Load Config",
  重新加载: "Reload",
  最大迭代次数: "Max Iterations",
  最大输入长度: "Max Input Length",
  心跳检测: "Heartbeat Check",
  刷新心跳: "Refresh Heartbeat",
  检测系统心跳: "Check Heartbeat",
  "网络连接失败：请确认后端服务可用并检查浏览器网络/代理设置。":
    "Network error: please ensure backend service is running and check browser network/proxy settings.",
  "从 ArXiv 搜索最新学术论文，快速了解研究动态":
    "Search the latest papers from ArXiv and get up to speed on current research quickly.",
  "按课题查看 workflow、claim、evidence、notes 和主动提醒。":
    "Inspect workflows, claims, evidence, notes, and proactive reminders by project.",
  活跃工作流: "Active Workflows",
  结构化笔记: "Structured Notes",
  证据项: "Evidence Items",
  项目列表: "Projects",
  "选择一个项目，下钻查看 workflow、claim 与提醒。":
    "Select a project to drill into workflows, claims, and reminders.",
  暂无研究项目: "No Research Projects",
  "先通过 API 创建 project，再在这里查看闭环进展。":
    "Create a project through the API first, then inspect closed-loop progress here.",
  项目概览: "Project Overview",
  "选择项目后显示聚合统计与近期活动。":
    "Aggregated stats and recent activity appear after you select a project.",
  "等待项目上下文": "Waiting For Project Context",
  "选中一个 project 后，这里会显示聚合指标。":
    "Select a project to display aggregate metrics here.",
  "工作流": "Workflows",
  "聚焦当前 stage、状态以及是否已经进入阻塞或写作阶段。":
    "Focus on the current stage, status, and whether the workflow is blocked or in writing.",
  "暂无工作流": "No Workflows",
  "当前项目还没有 workflow。": "This project does not have a workflow yet.",
  "执行健康度": "Execution Health",
  "汇总 project 下 experiment contract、bundle 校验和 remediation 压力。":
    "Summarize experiment contracts, bundle validation, and remediation pressure in the current project.",
  "等待健康度统计": "Waiting For Health Stats",
  "选中一个 project 后，这里会显示 execution health。":
    "Select a project to display execution health here.",
  "近期阻塞": "Recent Blockers",
  "优先显示 blocked workflow、未收口 remediation 和可重试实验。":
    "Prioritize blocked workflows, unresolved remediation, and retry-ready experiments.",
  "暂无显著阻塞": "No Major Blockers",
  "当前 project 没有需要优先处理的 contract 或 workflow blocker。":
    "This project has no contract or workflow blockers that need immediate attention.",
  "详情": "Details",
  "派发中...": "Dispatching...",
  派发: "Dispatch",
  "执行中...": "Executing...",
  执行: "Execute",
  "项目派发中...": "Dispatching Project Blockers...",
  "项目批量派发": "Dispatch Project Blockers",
  "项目执行中...": "Executing Project Blockers...",
  "项目批量执行": "Execute Project Blockers",
  "恢复可重试": "Resume Retry-Ready Workflows",
  "恢复中...": "Resuming...",
  "任务已派发。": "Task dispatched.",
  "任务已执行。": "Task executed.",
  "批量派发中...": "Dispatching Batch...",
  "批量派发": "Dispatch Batch",
  "批量执行中...": "Executing Batch...",
  "批量执行": "Execute Batch",
  "Remediation 详情": "Remediation Detail",
  "加载 remediation 上下文...": "Loading remediation context...",
  "暂无 remediation 摘要": "No remediation summary yet.",
  "Contract Failures": "Contract Failures",
  "暂无 contract failure": "No contract failures.",
  "Remediation Tasks": "Remediation Tasks",
  "暂无 remediation task": "No remediation tasks.",
  "继续推进": "Continue Workflow",
  "暂无 remediation 详情": "No Remediation Detail",
  "当前 workflow 没有可用的 remediation context。":
    "The current workflow does not have an available remediation context.",
  "Project blocker 操作失败": "Project blocker action failed",
  "主动提醒": "Proactive Reminders",
  "这里展示当前到期的 follow-up、写作待办和实验回看提醒。":
    "Shows due follow-ups, writing todos, and experiment review reminders.",
  "暂无到期提醒": "No Due Reminders",
  "当前没有需要主动推进的研究提醒。":
    "There are no active research reminders to push right now.",
  "Claim 与证据链": "Claims & Evidence",
  "打开某个 claim，查看它当前连接的 evidence、notes、artifacts 与 experiments。":
    "Open a claim to inspect linked evidence, notes, artifacts, and experiments.",
  "暂无 claim": "No Claims",
  "当前项目还没有结构化 claim。":
    "This project does not have structured claims yet.",
  "Claim 证据详情": "Claim Evidence Detail",
  "暂无证据": "No Evidence",
  "输入主题或关键词，从 ArXiv 获取相关研究论文":
    "Enter a topic or keywords to fetch relevant papers from ArXiv.",
  "输入研究主题关键词...": "Enter research topic keywords...",
  请尝试使用不同的关键词进行搜索:
    "Try searching with a different set of keywords.",
  "检索失败: {error}": "Search failed: {error}",
  "{count} 位作者": "{count} authors",
  等: "et al.",
  "集中查看服务健康、自动化执行、模型使用和控制面运行态。":
    "Inspect service health, automation runs, model usage, and control-plane runtime in one place.",
  热重载: "Hot Reload",
  服务总览: "Service Overview",
  "先确认健康、Agent 状态和能力装载，再下钻到具体链路。":
    "Confirm health, agent status, and loaded capabilities first, then drill into specific pipelines.",
  未知: "Unknown",
  运行时与模型: "Runtime & Models",
  "这里反映 Agent 实例规模、模型请求量和回退链是否在工作。":
    "This reflects agent instance scale, model request volume, and whether the fallback chain is working.",
  "Agent 实例": "Agent Instances",
  模型请求数: "Model Requests",
  回退次数: "Fallback Count",
  渠道与自动化: "Channels & Automation",
  "重点关注入口接入量、队列积压和自动化执行结果。":
    "Focus on ingress coverage, queue backlog, and automation execution results.",
  注册频道: "Registered Channels",
  通道队列消息: "Queued Messages",
  处理中会话键: "In-Progress Keys",
  自动化触发成功: "Automation Success",
  自动化触发失败: "Automation Failures",
  运行日志: "Runtime Logs",
  "最近 80 行，适合快速判断热重载、自动化和渠道是否有异常。":
    "Last 80 lines, useful for quickly checking hot reload, automation, and channel issues.",
  暂无日志: "No logs yet",
  "把内建频道、自定义插件、账号映射和路由绑定放在同一控制面里管理。":
    "Manage built-in channels, custom plugins, account mappings, and routing bindings in one control surface.",
  已注册: "Registered",
  目录总数: "Catalog Entries",
  自定义插件: "Custom Plugins",
  已注册频道: "Registered Channels",
  "运行时真正可用的入口，适合先看状态和类型。":
    "These are the actual runtime entry points; start here to inspect status and type.",
  "当前实例已经注册到运行时消息分发链路。":
    "The current instance is registered with the runtime message dispatch pipeline.",
  频道目录: "Channel Catalog",
  "内建与外部插件的统一目录，方便确认装载来源。":
    "A unified catalog for built-in and external plugins, useful for verifying load sources.",
  安装自定义频道: "Install Custom Channel",
  "可从本地路径或远程 URL 安装/更新，适合接 webhook、企业 IM 或自定义消息入口。":
    "Install or update from a local path or remote URL, suitable for webhooks, enterprise IM, or custom message ingress.",
  "安装/更新插件": "Install / Update Plugin",
  暂无自定义插件: "No custom plugins",
  账号与绑定配置: "Accounts & Bindings",
  "账号实例和 bindings 直接影响消息路由，保存后会热重载到运行时。":
    "Account instances and bindings directly affect message routing and hot-reload into runtime after saving.",
  保存并热重载: "Save & Hot Reload",
  "Agent 视图": "Agent View",
  "全部 Agent": "All Agents",
  搜索: "Search",
  会话列表: "Session List",
  "管理周期性执行的自动化任务，覆盖编辑、删除、立即执行、通道设置和运行时限制。":
    "Manage recurring automation jobs, including edit, delete, run-now, channel settings, and runtime limits.",
  任务数: "Jobs",
  启用中: "Enabled",
  可用通道: "Available Channels",
  状态: "Status",
  全部状态: "All Statuses",
  任务列表: "Job List",
  "建议把高价值、可重复的研究流程沉淀为定时任务，并明确通道和目标会话。":
    "Turn high-value, repeatable research workflows into scheduled jobs, with explicit channels and target sessions.",
  "查看心跳任务的当前配置与运行状态，确认系统是否会按周期自动唤醒。":
    "Inspect the current heartbeat configuration and runtime status to confirm periodic wake-ups are active.",
  频率: "Frequency",
  "Heartbeat 配置": "Heartbeat Config",
  "当前返回的是运行时心跳配置的原始结构，适合排查调度目标与参数。":
    "This returns the raw runtime heartbeat config, useful for troubleshooting scheduling targets and parameters.",
  "集中查看并编辑关键运行文件，把配置、技能、心跳、定时和记忆内容维持在同一工作区里。":
    "Inspect and edit key runtime files in one workspace, keeping config, skills, heartbeat, schedules, and memory together.",
  当前文件: "Current File",
  编辑状态: "Edit Status",
  工作区关系图: "Workspace Map",
  "帮助你快速确认会话、技能、定时任务、心跳和配置之间的连接关系。":
    "Helps you quickly confirm relationships among sessions, skills, scheduled jobs, heartbeat, and config.",
  "按分类快速切换，适合维护 `config.json`、`AGENTS.md` 等核心文件。":
    "Switch by category quickly, ideal for maintaining core files such as `config.json` and `AGENTS.md`.",
  "启用或禁用 Agent 技能，同时影响聊天和 `task_type=agent` 的定时任务。":
    "Enable or disable agent skills, affecting both chat and `task_type=agent` scheduled jobs.",
  技能总数: "Skills",
  技能开关: "Skill Toggles",
  "建议只启用你当前需要的能力，避免让 Agent 在低价值技能上分散注意力。":
    "Enable only the capabilities you need right now, so the agent does not get distracted by low-value skills.",
  "把高频运行参数放在一处调优，平衡推理深度、上下文长度和交互速度。":
    "Tune high-frequency runtime parameters in one place to balance reasoning depth, context length, and interaction speed.",
  最大迭代: "Max Iterations",
  上下文上限: "Context Limit",
  推理步数: "Reasoning Steps",
  "适合控制任务深度。数值越高，复杂任务成功率更高，但成本和时延也会上升。":
    "Useful for controlling task depth. Higher values improve complex task success rates, but increase cost and latency.",
  "Agent 单次任务的最大推理步数":
    "Maximum reasoning steps allowed for a single agent task",
  上下文容量: "Context Capacity",
  "适合控制单次任务能容纳的上下文长度，直接影响长论文和长工具输出的可处理范围。":
    "Useful for controlling how much context a single task can hold, directly affecting long papers and long tool outputs.",
  "单次输入的最大 token 数量": "Maximum tokens allowed for a single input",
  "一个供应商卡片对应一个平台入口，可挂多个模型，并直接应用到当前 Agent 运行配置。":
    "Each provider card represents one platform endpoint, can host multiple models, and can be applied directly to the current agent runtime config.",
  供应商: "Providers",
  可发现模型: "Discoverable Models",
  供应商列表: "Provider List",
  "启用仅代表该入口可用；“应用”会把当前入口写入 Agent 的活动模型配置。":
    'Enabled only means the endpoint is available; "Apply" writes the current endpoint into the agent\'s active model config.',
  "管理 API 密钥和环境配置参数":
    "Manage API keys and environment configuration parameters",
  "管理 Model Context Protocol 客户端连接":
    "Manage Model Context Protocol client connections",
  "Cron: {cron} ({timezone})": "Cron: {cron} ({timezone})",
  "类型: {taskType}": "Type: {taskType}",
  "目标: {user}/{session}": "Target: {user}/{session}",
  "模式: {mode}": "Mode: {mode}",
  "流式连接超时：后端响应过慢或网络不稳定。":
    "Stream timeout: backend is slow or network is unstable.",
  "流式连接中断：长时间未收到数据，请重试。":
    "Stream interrupted: no data received for a while. Please retry.",
  "流式连接已结束，但未收到完成信号。":
    "Stream closed without a completion signal.",
  "流式连接未返回有效数据。": "No valid data from streaming connection.",
  "(已停止)": "(Stopped)",
};

function normalizeLocale(input: string | null | undefined): Locale {
  if (!input) return "zh";
  const v = input.toLowerCase();
  if (v.startsWith("en")) return "en";
  return "zh";
}

function formatTemplate(
  template: string,
  vars?: Record<string, unknown>,
): string {
  if (!vars) return template;
  let out = template;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replace(new RegExp(`\\{${k}\\}`, "g"), String(v ?? ""));
  }
  return out;
}

export function translateText(
  locale: Locale,
  text: string,
  vars?: Record<string, unknown>,
): string {
  const source = String(text ?? "");
  if (!source) return source;
  if (locale === "zh") return formatTemplate(source, vars);

  if (EN_DICT[source]) return formatTemplate(EN_DICT[source], vars);

  const leading = source.match(/^\s*/)?.[0] ?? "";
  const trailing = source.match(/\s*$/)?.[0] ?? "";
  const core = source.slice(leading.length, source.length - trailing.length);
  if (EN_DICT[core]) {
    return `${leading}${formatTemplate(EN_DICT[core], vars)}${trailing}`;
  }
  return formatTemplate(source, vars);
}

export function getStoredLocale(): Locale {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return normalizeLocale(raw);
  } catch {
    // ignore
  }
  if (typeof navigator !== "undefined") {
    return normalizeLocale(navigator.language);
  }
  return "zh";
}

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (text: string, vars?: Record<string, unknown>) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => getStoredLocale());

  useEffect(() => {
    let cancelled = false;
    let shouldFetch = true;
    try {
      shouldFetch = !localStorage.getItem(STORAGE_KEY);
    } catch {
      shouldFetch = true;
    }
    if (!shouldFetch) return () => {};

    void fetch("/api/config")
      .then(async (res) => (res.ok ? res.json() : {}))
      .then((cfg) => {
        if (cancelled) return;
        const lang = typeof cfg?.language === "string" ? cfg.language : "";
        if (lang) {
          setLocaleState(normalizeLocale(lang));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const setLocale = useCallback((next: Locale) => {
    const normalized = normalizeLocale(next);
    setLocaleState(normalized);
    try {
      localStorage.setItem(STORAGE_KEY, normalized);
    } catch {
      // ignore
    }
    const payload = { language: normalized === "zh" ? "zh" : "en" };
    void fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {});
  }, []);

  const t = useCallback(
    (text: string, vars?: Record<string, unknown>) =>
      translateText(locale, text, vars),
    [locale],
  );

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t,
    }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}

const TRANSLATABLE_ATTRS = [
  "placeholder",
  "title",
  "aria-label",
  "alt",
  "data-tooltip",
] as const;
const ORIGINAL_TEXT_NODES = new WeakMap<Text, string>();
const ORIGINAL_ATTRS = new WeakMap<Element, Record<string, string>>();

function _is_skippable_text_node(node: Text): boolean {
  const parent = node.parentElement;
  if (!parent) return true;

  const tag = parent.tagName.toLowerCase();
  if (tag === "script" || tag === "style" || tag === "noscript") return true;
  if (parent.closest("textarea, input, code, pre")) return true;
  if (parent.closest("[data-no-auto-translate]")) return true;
  if (parent.isContentEditable) return true;
  return false;
}

function _apply_text_translations(root: HTMLElement, locale: Locale): void {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let cur = walker.nextNode();
  while (cur) {
    const node = cur as Text;
    const raw = node.nodeValue ?? "";
    if (raw.trim() && !_is_skippable_text_node(node)) {
      if (!ORIGINAL_TEXT_NODES.has(node)) {
        ORIGINAL_TEXT_NODES.set(node, raw);
      }
      let original = ORIGINAL_TEXT_NODES.get(node) ?? raw;
      const translatedOriginal = translateText("en", original);
      if (raw !== original && raw !== translatedOriginal) {
        ORIGINAL_TEXT_NODES.set(node, raw);
        original = raw;
      }
      const next = locale === "en" ? translateText("en", original) : original;
      if (node.nodeValue !== next) {
        node.nodeValue = next;
      }
    }
    cur = walker.nextNode();
  }
}

function _apply_attr_translations(root: HTMLElement, locale: Locale): void {
  const selector = TRANSLATABLE_ATTRS.map((x) => `[${x}]`).join(",");
  if (!selector) return;

  root.querySelectorAll(selector).forEach((el) => {
    if (el.closest("[data-no-auto-translate]")) {
      return;
    }
    let record = ORIGINAL_ATTRS.get(el);
    if (!record) {
      record = {};
      ORIGINAL_ATTRS.set(el, record);
    }

    for (const attr of TRANSLATABLE_ATTRS) {
      const value = el.getAttribute(attr);
      if (value == null) continue;
      if (!(attr in record)) {
        record[attr] = value;
      }
      let original = record[attr] ?? value;
      const translatedOriginal = translateText("en", original);
      if (value !== original && value !== translatedOriginal) {
        record[attr] = value;
        original = value;
      }
      const next = locale === "en" ? translateText("en", original) : original;
      if (value !== next) {
        el.setAttribute(attr, next);
      }
    }
  });
}

function _apply_dom_translations(root: HTMLElement, locale: Locale): void {
  _apply_text_translations(root, locale);
  _apply_attr_translations(root, locale);
}

export function AutoTranslate({ children }: { children: React.ReactNode }) {
  const { locale } = useI18n();

  useEffect(() => {
    const root = document.getElementById("root");
    if (!root) return () => {};

    let rafId: number | null = null;
    const run = () => {
      rafId = null;
      _apply_dom_translations(root, locale);
    };

    run();

    const observer = new MutationObserver(() => {
      if (rafId != null) {
        cancelAnimationFrame(rafId);
      }
      rafId = requestAnimationFrame(run);
    });

    observer.observe(root, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: [...TRANSLATABLE_ATTRS],
    });

    return () => {
      observer.disconnect();
      if (rafId != null) {
        cancelAnimationFrame(rafId);
      }
    };
  }, [locale]);

  return <>{children}</>;
}
