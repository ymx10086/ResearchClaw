import React, {
  createContext,
  isValidElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type Locale = "zh" | "en";

const STORAGE_KEY = "researchclaw.console.locale";

const EN_DICT: Record<string, string> = {
  研究: "Research",
  控制: "Control",
  智能体: "Agent",
  设置: "Settings",
  "AI 对话": "AI Chat",
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
  "任务名称不能为空": "Task name cannot be empty",
  "文本内容不能为空": "Text content cannot be empty",
  "Agent 提示词不能为空": "Agent prompt cannot be empty",
  "确认删除定时任务「{name}」吗？":
    "Are you sure you want to delete scheduled job \"{name}\"?",
  '确定删除供应商 "{name}"？':
    'Are you sure you want to delete provider "{name}"?',
  "通道 (默认 console)": "Channel (default: console)",
  "马上运行": "Run Now",
  "编辑定时任务": "Edit Job",
  "新建定时任务": "New Job",
  "加载定时任务": "Loading Jobs",
  "暂无定时任务": "No Scheduled Jobs",
  "刷新任务": "Refresh Jobs",
  "点击刷新加载频道": "Click Refresh to Load Channels",
  "频道管理": "Channel Management",
  "刷新频道": "Refresh Channels",
  "会话管理": "Session Management",
  "刷新会话": "Refresh Sessions",
  "会话详情": "Session Detail",
  "开始一段研究对话": "Start a Research Conversation",
  "暂无历史会话": "No Chat History",
  "当前会话: ": "Current Session: ",
  未创建: "Not Created",
  "思考过程": "Reasoning",
  "正在思考...": "Thinking...",
  "加载工作区信息": "Loading Workspace",
  "工作区文件": "Workspace Files",
  "刷新工作区": "Refresh Workspace",
  "关键文件": "Key Files",
  必需: "Required",
  "请选择文件": "Please select a file",
  "加载文件中...": "Loading file...",
  对话: "Chat",
  配置: "Config",
  "对话 / 技能 / 定时 / 心跳 关系":
    "Chat / Skills / Schedules / Heartbeat Relations",
  "刷新状态": "Refresh Status",
  "API 健康": "API Health",
  正常: "Healthy",
  "运行状态": "Runtime",
  运行中: "Running",
  已停止: "Stopped",
  "可用工具": "Available Tools",
  "激活技能": "Active Skills",
  关闭: "Off",
  "运行模式": "Run Mode",
  "运行时长": "Uptime",
  "加载技能列表": "Loading Skills",
  "技能管理": "Skill Management",
  "刷新技能": "Refresh Skills",
  "加载环境变量": "Loading Environment Variables",
  "检索 ArXiv": "Search ArXiv",
  "未找到相关论文": "No relevant papers found",
  "搜索学术论文": "Search Academic Papers",
  "MCP 客户端": "MCP Clients",
  "新增客户端": "New Client",
  "加载 MCP 客户端": "Loading MCP Clients",
  "添加新客户端": "Add New Client",
  "新增供应商": "Add Provider",
  "供应商类型": "Provider Type",
  "模型名称": "Model Name",
  "应用到 Agent（热重载）": "Apply to Agent (hot reload)",
  应用: "Apply",
  "保存设置": "Save Settings",
  "模型 & 供应商": "Models & Providers",
  "加载供应商配置": "Loading Provider Config",
  "暂无供应商": "No Providers",
  "加载 Agent 配置": "Loading Agent Config",
  "加载配置": "Load Config",
  "重新加载": "Reload",
  "最大迭代次数": "Max Iterations",
  "最大输入长度": "Max Input Length",
  "心跳检测": "Heartbeat Check",
  "刷新心跳": "Refresh Heartbeat",
  "检测系统心跳": "Check Heartbeat",
  "网络连接失败：请确认后端服务可用并检查浏览器网络/代理设置。":
    "Network error: please ensure backend service is running and check browser network/proxy settings.",
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

function formatTemplate(template: string, vars?: Record<string, unknown>): string {
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

const TEXT_PROP_KEYS = new Set([
  "children",
  "placeholder",
  "title",
  "aria-label",
  "alt",
]);

function translateNode(
  node: React.ReactNode,
  t: (text: string) => string,
): React.ReactNode {
  if (node == null || typeof node === "boolean" || typeof node === "number") {
    return node;
  }
  if (typeof node === "string") {
    return t(node);
  }
  if (Array.isArray(node)) {
    return node.map((item) => translateNode(item, t));
  }
  if (!isValidElement(node)) {
    return node;
  }

  const props = (node.props || {}) as Record<string, unknown>;
  const nextProps: Record<string, unknown> = {};
  let changed = false;

  for (const [key, value] of Object.entries(props)) {
    if (key === "children") {
      const nextChildren = translateNode(value as React.ReactNode, t);
      nextProps[key] = nextChildren;
      if (nextChildren !== value) changed = true;
      continue;
    }
    if (typeof value === "string" && TEXT_PROP_KEYS.has(key)) {
      const translated = t(value);
      nextProps[key] = translated;
      if (translated !== value) changed = true;
      continue;
    }
    nextProps[key] = value;
  }

  if (!changed) return node;
  return React.cloneElement(node, nextProps);
}

export function AutoTranslate({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const tr = useCallback((text: string) => t(text), [t]);
  return <>{translateNode(children, tr)}</>;
}
