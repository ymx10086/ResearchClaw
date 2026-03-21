import { useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  MessageSquare,
  FileText,
  Radio,
  MessageCircle,
  Timer,
  Heart,
  Activity,
  Workflow,
  FolderOpen,
  Puzzle,
  Cable,
  Settings,
  Cpu,
  KeyRound,
  Menu,
  X,
  Github,
  BookOpen,
  Users,
  Mail,
  ChevronDown,
  type LucideIcon,
} from "lucide-react";
import ChatPage from "./pages/ChatPage";
import PapersPage from "./pages/PapersPage";
import ResearchPage from "./pages/ResearchPage";
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

type NavItemConfig = {
  to: string;
  label: string;
  icon: LucideIcon;
  tone:
    | "brand"
    | "teal"
    | "blue"
    | "green"
    | "amber"
    | "danger"
    | "violet"
    | "slate";
};

type NavSection = {
  title: string;
  items: NavItem[];
};

type NavSectionConfig = {
  title: string;
  items: NavItemConfig[];
};

type TopLink = {
  label: string;
  href: string;
  icon: React.ReactNode;
};

const navSectionConfigs: NavSectionConfig[] = [
  {
    title: "研究",
    items: [
      {
        to: "/research",
        label: "研究项目",
        icon: Workflow,
        tone: "amber",
      },
      {
        to: "/chat",
        label: "AI 对话",
        icon: MessageSquare,
        tone: "brand",
      },
      {
        to: "/papers",
        label: "论文检索",
        icon: FileText,
        tone: "teal",
      },
    ],
  },
  {
    title: "控制",
    items: [
      {
        to: "/channels",
        label: "频道",
        icon: Radio,
        tone: "blue",
      },
      {
        to: "/sessions",
        label: "会话",
        icon: MessageCircle,
        tone: "green",
      },
      {
        to: "/cron-jobs",
        label: "定时任务",
        icon: Timer,
        tone: "amber",
      },
      {
        to: "/heartbeat",
        label: "心跳",
        icon: Heart,
        tone: "danger",
      },
      {
        to: "/status",
        label: "系统状态",
        icon: Activity,
        tone: "violet",
      },
    ],
  },
  {
    title: "智能体",
    items: [
      {
        to: "/workspace",
        label: "工作区",
        icon: FolderOpen,
        tone: "slate",
      },
      {
        to: "/skills",
        label: "技能",
        icon: Puzzle,
        tone: "brand",
      },
      {
        to: "/mcp",
        label: "MCP",
        icon: Cable,
        tone: "teal",
      },
      {
        to: "/agent-config",
        label: "Agent 配置",
        icon: Settings,
        tone: "violet",
      },
    ],
  },
  {
    title: "设置",
    items: [
      {
        to: "/models",
        label: "模型",
        icon: Cpu,
        tone: "blue",
      },
      {
        to: "/environments",
        label: "环境变量",
        icon: KeyRound,
        tone: "amber",
      },
    ],
  },
];

function renderNavIcon(
  Icon: LucideIcon,
  tone: NavItemConfig["tone"],
): React.ReactNode {
  return (
    <IconBadge tone={tone} size="sm">
      <Icon size={14} />
    </IconBadge>
  );
}

function buildNavSections(): NavSection[] {
  return navSectionConfigs.map((section) => ({
    title: section.title,
    items: section.items.map((item) => ({
      to: item.to,
      label: item.label,
      icon: renderNavIcon(item.icon, item.tone),
    })),
  }));
}

function buildTopLinks(locale: "zh" | "en"): TopLink[] {
  return [
    {
      label: "GitHub",
      href: "https://github.com/ymx10086/ResearchClaw",
      icon: <Github size={14} />,
    },
    {
      label: locale === "zh" ? "社区" : "Community",
      href: "https://github.com/orgs/Research-Equality/repositories",
      icon: <Users size={14} />,
    },
    {
      label: "Email",
      href: "mailto:mxyang25@stu.pku.edu.cn",
      icon: <Mail size={14} />,
    },
    {
      label: locale === "zh" ? "文档" : "Docs",
      href: "https://ymx10086.github.io/ResearchClaw/",
      icon: <BookOpen size={14} />,
    },
    {
      label: locale === "zh" ? "关于我" : "About Me",
      href: "https://github.com/ymx10086",
      icon: <Github size={14} />,
    },
  ];
}

export default function App() {
  const location = useLocation();
  const { locale, setLocale, t } = useI18n();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navSections = buildNavSections();
  const topLinks = buildTopLinks(locale);

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
              <p className="brand-mission">{t("让重复退场，让创造登场。")}</p>
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
          <div className="sidebar-footer-badge">
            <span className="sidebar-footer-dot" />
            {t("ResearchClaw 运行中")}
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label={t("关闭导航")}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="content">
        <div className="console-topbar">
          <div className="console-topbar-left">
            <button
              type="button"
              className="mobile-sidebar-toggle"
              aria-label={sidebarOpen ? t("关闭导航") : t("打开导航")}
              onClick={() => setSidebarOpen((value) => !value)}
            >
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <nav className="console-topnav" aria-label="Console Links">
              {topLinks.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  className="console-topnav-link"
                  target="_blank"
                  rel="noreferrer"
                >
                  {item.icon}
                  <span>{item.label}</span>
                </a>
              ))}
            </nav>
          </div>
          <div className="console-topbar-right">
            <label className="console-locale-picker">
              <span className="console-locale-label">{t("语言")}</span>
              <div className="console-locale-select-wrap">
                <select
                  value={locale}
                  onChange={(e) => setLocale(e.target.value as "zh" | "en")}
                  aria-label={t("切换语言")}
                >
                  <option value="zh">{t("中文")}</option>
                  <option value="en">English</option>
                </select>
                <ChevronDown size={14} className="console-locale-chevron" />
              </div>
            </label>
          </div>
        </div>
        <ConsoleCronBubble />
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<ChatPage />} />
          <Route path="/research" element={<ResearchPage />} />
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
