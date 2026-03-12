import { useMemo, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  MessageSquare,
  FileText,
  Radio,
  MessageCircle,
  Timer,
  Heart,
  Activity,
  FolderOpen,
  Puzzle,
  Cable,
  Settings,
  Cpu,
  KeyRound,
  Menu,
  X,
  Sparkles,
} from "lucide-react";
import ChatPage from "./pages/ChatPage";
import PapersPage from "./pages/PapersPage";
import StatusPage from "./pages/StatusPage";
import ChannelsPage from "./pages/ChannelsPage";
import SessionsPage from "./pages/SessionsPage";
import CronJobsPage from "./pages/CronJobsPage";
import HeartbeatPage from "./pages/HeartbeatPage";
import EnvironmentsPage from "./pages/EnvironmentsPage";
import SkillsPage from "./pages/SkillsPage";
import McpPage from "./pages/McpPage";
import WorkspacePage from "./pages/WorkspacePage";
import AgentConfigPage from "./pages/AgentConfigPage";
import ModelsPage from "./pages/ModelsPage";
import ConsoleCronBubble from "./components/ConsoleCronBubble";
import { IconBadge } from "./components/icons";
import { useI18n } from "./i18n";

type NavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
};

type NavSection = {
  title: string;
  items: NavItem[];
};

const navSections: NavSection[] = [
  {
    title: "研究",
    items: [
      {
        to: "/chat",
        label: "AI 对话",
        icon: (
          <IconBadge tone="brand" size="sm">
            <MessageSquare size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/papers",
        label: "论文检索",
        icon: (
          <IconBadge tone="teal" size="sm">
            <FileText size={14} />
          </IconBadge>
        ),
      },
    ],
  },
  {
    title: "控制",
    items: [
      {
        to: "/channels",
        label: "频道",
        icon: (
          <IconBadge tone="blue" size="sm">
            <Radio size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/sessions",
        label: "会话",
        icon: (
          <IconBadge tone="green" size="sm">
            <MessageCircle size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/cron-jobs",
        label: "定时任务",
        icon: (
          <IconBadge tone="amber" size="sm">
            <Timer size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/heartbeat",
        label: "心跳",
        icon: (
          <IconBadge tone="danger" size="sm">
            <Heart size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/status",
        label: "系统状态",
        icon: (
          <IconBadge tone="violet" size="sm">
            <Activity size={14} />
          </IconBadge>
        ),
      },
    ],
  },
  {
    title: "智能体",
    items: [
      {
        to: "/workspace",
        label: "工作区",
        icon: (
          <IconBadge tone="slate" size="sm">
            <FolderOpen size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/skills",
        label: "技能",
        icon: (
          <IconBadge tone="brand" size="sm">
            <Puzzle size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/mcp",
        label: "MCP",
        icon: (
          <IconBadge tone="teal" size="sm">
            <Cable size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/agent-config",
        label: "Agent 配置",
        icon: (
          <IconBadge tone="violet" size="sm">
            <Settings size={14} />
          </IconBadge>
        ),
      },
    ],
  },
  {
    title: "设置",
    items: [
      {
        to: "/models",
        label: "模型",
        icon: (
          <IconBadge tone="blue" size="sm">
            <Cpu size={14} />
          </IconBadge>
        ),
      },
      {
        to: "/environments",
        label: "环境变量",
        icon: (
          <IconBadge tone="amber" size="sm">
            <KeyRound size={14} />
          </IconBadge>
        ),
      },
    ],
  },
];

export default function App() {
  const location = useLocation();
  const { locale, setLocale } = useI18n();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const currentSection = useMemo(() => {
    for (const section of navSections) {
      for (const item of section.items) {
        if (
          location.pathname === item.to ||
          (item.to === "/chat" && location.pathname === "/")
        ) {
          return {
            section: section.title,
            label: item.label,
          };
        }
      }
    }
    return {
      section: "研究",
      label: "AI 对话",
    };
  }, [location.pathname]);

  const pageDescriptions: Record<string, string> = {
    "AI 对话": "围绕论文检索、分析、写作和实验设计持续推进研究任务。",
    论文检索: "组织检索结果、筛选候选文献，并快速沉淀研究线索。",
    频道: "管理多渠道接入、账号绑定和自定义插件，让入口更稳定。",
    会话: "按 Agent 追踪会话流转，快速恢复历史上下文。",
    定时任务: "用计划任务驱动自动化触发，减少人工操作。",
    心跳: "维持定期唤醒与调度，让自动化链路保持在线。",
    系统状态: "集中查看服务健康、自动化执行和控制面运行态。",
    工作区: "围绕配置、技能、心跳和任务文件统一维护研究工作区。",
    技能: "管理当前启用技能，明确各类能力边界和状态。",
    MCP: "连接外部工具、资源和服务，扩展 Agent 的研究能力。",
    "Agent 配置": "调整运行参数，平衡成本、上下文和推理深度。",
    模型: "配置主模型、回退链和模型能力分配。",
    环境变量: "管理部署时依赖的外部密钥和运行参数。",
  };

  return (
    <div className="layout">
      <aside className={`sidebar${sidebarOpen ? " open" : ""}`}>
        <div className="brand">
          <div className="brand-title">
            <div className="brand-logo">
              <img
                src="/researchclaw-symbol.png"
                alt="ResearchClaw Symbol"
                className="brand-symbol-img"
              />
            </div>
            <div>
              <img
                src="/researchclaw-logo.png"
                alt="ResearchClaw"
                className="brand-wordmark-img"
              />
              <p>Scholar Console</p>
            </div>
          </div>
        </div>

        <nav className="menu">
          {navSections.map((section) => (
            <div key={section.title} className="nav-section">
              <div className="nav-section-label">{section.title}</div>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `nav-link${isActive ? " active" : ""}`
                  }
                  onClick={() => setSidebarOpen(false)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-spotlight">
            <div className="sidebar-spotlight-label">Research Ops</div>
            <strong>多渠道 + 自动化 + 中控台</strong>
            <p>当前控制台已覆盖运行态、渠道接入与工作区编辑。</p>
          </div>
          <div className="sidebar-footer-badge">
            <span className="sidebar-footer-dot" />
            ResearchClaw 运行中
          </div>
          <div className="lang-switch">
            <button
              type="button"
              className={`lang-btn${locale === "zh" ? " active" : ""}`}
              onClick={() => setLocale("zh")}
            >
              中文
            </button>
            <button
              type="button"
              className={`lang-btn${locale === "en" ? " active" : ""}`}
              onClick={() => setLocale("en")}
            >
              EN
            </button>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="关闭导航"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="content">
        <header className="app-topbar">
          <div className="app-topbar-main">
            <button
              type="button"
              className="app-topbar-menu"
              aria-label={sidebarOpen ? "关闭导航" : "打开导航"}
              onClick={() => setSidebarOpen((value) => !value)}
            >
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <div>
              <div className="app-topbar-breadcrumb">
                <span>{currentSection.section}</span>
                <span>/</span>
                <span>{currentSection.label}</span>
              </div>
              <div className="app-topbar-title">{currentSection.label}</div>
              <p>
                {pageDescriptions[currentSection.label] ||
                  "ResearchClaw 控制台"}
              </p>
            </div>
          </div>
          <div className="app-topbar-status">
            <div className="app-topbar-pill">
              <Sparkles size={14} />
              Scholar Console
            </div>
            <div className="app-topbar-pill subtle">{locale.toUpperCase()}</div>
          </div>
        </header>
        <ConsoleCronBubble />
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<ChatPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/papers" element={<PapersPage />} />
          <Route path="/channels" element={<ChannelsPage />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/cron-jobs" element={<CronJobsPage />} />
          <Route path="/heartbeat" element={<HeartbeatPage />} />
          <Route path="/status" element={<StatusPage />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/skills" element={<SkillsPage />} />
          <Route path="/agent-config" element={<AgentConfigPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/environments" element={<EnvironmentsPage />} />
          <Route path="/mcp" element={<McpPage />} />
        </Routes>
      </main>
    </div>
  );
}
