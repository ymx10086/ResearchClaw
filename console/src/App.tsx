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
  Beaker,
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

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">
            <div className="brand-logo">
              <Beaker size={20} />
            </div>
            <div>
              <h1>ResearchClaw</h1>
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

      <main className="content">
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
