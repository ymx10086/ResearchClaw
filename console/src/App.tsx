import { useMemo, useState } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import {
  createMcpClient,
  deleteMcpClient,
  deleteSession,
  disableSkill,
  enableSkill,
  getAgentRunningConfig,
  getChannels,
  getControlStatus,
  getCronJobs,
  getHealth,
  getHeartbeat,
  getSessionDetail,
  getSessions,
  getStatus,
  getWorkspaceProfile,
  getWorkspaceInfo,
  listActiveSkills,
  listAvailableModels,
  listEnvVars,
  listProviders,
  listSkills,
  listMcpClients,
  saveEnvVars,
  searchArxiv,
  sendChat,
  toggleCronJob,
  toggleMcpClient,
  updateAgentRunningConfig,
} from "./api";
import type {
  AgentRunningConfig,
  ChannelItem,
  ChatMessage,
  CronJobItem,
  McpClientItem,
  PaperItem,
  SessionItem,
  SkillItem,
} from "./types";

function formatTs(ts?: number): string {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString();
}

function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [chatLoading, setChatLoading] = useState(false);

  const canSend = useMemo(
    () => chatInput.trim().length > 0 && !chatLoading,
    [chatInput, chatLoading],
  );

  async function onSendChat() {
    const text = chatInput.trim();
    if (!text) return;
    setChatLoading(true);
    setMessages((prev: ChatMessage[]) => [
      ...prev,
      { role: "user", content: text },
    ]);
    setChatInput("");

    try {
      const res = await sendChat(text, sessionId);
      setSessionId(res.session_id);
      setMessages((prev: ChatMessage[]) => [
        ...prev,
        { role: "assistant", content: res.response },
      ]);
    } catch (error) {
      setMessages((prev: ChatMessage[]) => [
        ...prev,
        { role: "assistant", content: `请求失败: ${String(error)}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Chat</h2>
      <div className="messages">
        {messages.length === 0 && (
          <p className="muted">
            开始和 Scholar 对话：文献综述、实验设计、写作润色等。
          </p>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`msg ${msg.role}`}>
            <strong>{msg.role === "user" ? "你" : "Scholar"}:</strong>{" "}
            {msg.content}
          </div>
        ))}
      </div>
      <div className="row">
        <input
          value={chatInput}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setChatInput(e.target.value)
          }
          placeholder="例如：帮我总结 Diffusion Models 近两年趋势"
          onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter" && canSend) onSendChat();
          }}
        />
        <button onClick={onSendChat} disabled={!canSend}>
          {chatLoading ? "发送中..." : "发送"}
        </button>
      </div>
      {sessionId && <p className="muted">Session: {sessionId}</p>}
    </section>
  );
}

function PapersPage() {
  const [paperQuery, setPaperQuery] = useState(
    "large language model reasoning",
  );
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [paperLoading, setPaperLoading] = useState(false);

  async function onSearchPapers() {
    if (!paperQuery.trim()) return;
    setPaperLoading(true);
    try {
      const result = await searchArxiv(paperQuery);
      setPapers(result);
    } catch (error) {
      setPapers([{ title: `检索失败: ${String(error)}` }]);
    } finally {
      setPaperLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Papers</h2>
      <div className="row">
        <input
          value={paperQuery}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setPaperQuery(e.target.value)
          }
          placeholder="输入检索主题"
        />
        <button onClick={onSearchPapers} disabled={paperLoading}>
          {paperLoading ? "检索中..." : "检索 ArXiv"}
        </button>
      </div>
      <div className="list">
        {papers.map((paper, idx) => (
          <div key={idx} className="card">
            <h3>{paper.title || "Untitled"}</h3>
            {paper.id && (
              <p>
                <strong>ID:</strong> {paper.id}
              </p>
            )}
            {paper.published && (
              <p>
                <strong>Published:</strong> {paper.published}
              </p>
            )}
            {paper.authors && paper.authors.length > 0 && (
              <p>
                <strong>Authors:</strong> {paper.authors.join(", ")}
              </p>
            )}
            {paper.summary && (
              <p className="muted">{paper.summary.slice(0, 240)}...</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function StatusPage() {
  const [health, setHealth] = useState<string>("unknown");
  const [agentInfo, setAgentInfo] = useState<string>("not loaded");
  const [control, setControl] = useState<any>(null);

  async function onRefreshStatus() {
    try {
      const h = await getHealth();
      setHealth(h.status);
    } catch {
      setHealth("down");
    }

    try {
      const s = await getStatus();
      setAgentInfo(
        `${s.agent_name} | running=${String(s.running)} | tools=${
          s.tool_count
        }`,
      );
    } catch (error) {
      setAgentInfo(`status error: ${String(error)}`);
    }

    try {
      setControl(await getControlStatus());
    } catch {
      setControl(null);
    }
  }

  return (
    <section className="panel">
      <h2>Status</h2>
      <button onClick={onRefreshStatus}>刷新状态</button>
      <p>
        <strong>API Health:</strong> {health}
      </p>
      <p>
        <strong>Agent:</strong> {agentInfo}
      </p>
      {control && (
        <>
          <p>
            <strong>Mode:</strong> {control.mode}
          </p>
          <p>
            <strong>Uptime(s):</strong> {control.uptime_seconds}
          </p>
          <p>
            <strong>Cron Jobs:</strong>{" "}
            {Array.isArray(control.cron_jobs) ? control.cron_jobs.length : 0}
          </p>
        </>
      )}
    </section>
  );
}

function ChannelsPage() {
  const [channels, setChannels] = useState<ChannelItem[]>([]);

  async function onLoad() {
    setChannels(await getChannels());
  }

  return (
    <section className="panel">
      <h2>Channels</h2>
      <button onClick={onLoad}>刷新频道</button>
      <div className="list">
        {channels.map((item: ChannelItem, idx: number) => (
          <div key={idx} className="card">
            <p>
              <strong>Name:</strong> {item.name}
            </p>
            <p>
              <strong>Type:</strong> {item.type}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function SessionsPage() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [selected, setSelected] = useState<any>(null);

  async function onLoad() {
    setSessions(await getSessions());
  }

  async function onOpen(sessionId: string) {
    setSelected(await getSessionDetail(sessionId));
  }

  async function onDelete(sessionId: string) {
    await deleteSession(sessionId);
    if (selected?.session_id === sessionId) {
      setSelected(null);
    }
    await onLoad();
  }

  return (
    <section className="panel">
      <h2>Sessions</h2>
      <button onClick={onLoad}>刷新会话</button>
      <div className="list">
        {sessions.map((session: SessionItem) => (
          <div key={session.session_id} className="card">
            <p>
              <strong>ID:</strong> {session.session_id}
            </p>
            <p>
              <strong>Title:</strong> {session.title || "-"}
            </p>
            <p>
              <strong>Messages:</strong> {session.message_count ?? 0}
            </p>
            <p className="muted">Updated: {formatTs(session.updated_at)}</p>
            <div className="row">
              <button onClick={() => onOpen(session.session_id)}>查看</button>
              <button
                className="danger"
                onClick={() => onDelete(session.session_id)}
              >
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
      {selected && (
        <pre className="pre">{JSON.stringify(selected, null, 2)}</pre>
      )}
    </section>
  );
}

function CronJobsPage() {
  const [jobs, setJobs] = useState<CronJobItem[]>([]);

  async function onLoad() {
    setJobs(await getCronJobs());
  }

  async function onToggle(name: string, enabled: boolean) {
    await toggleCronJob(name, enabled);
    await onLoad();
  }

  return (
    <section className="panel">
      <h2>Cron Jobs</h2>
      <button onClick={onLoad}>刷新任务</button>
      <div className="list">
        {jobs.map((job: CronJobItem) => (
          <div key={job.name} className="card row spread">
            <div>
              <p>
                <strong>{job.name}</strong>
              </p>
              <p className="muted">
                interval: {job.interval_seconds}s | running:{" "}
                {String(job.running)}
              </p>
            </div>
            <button onClick={() => onToggle(job.name, !job.enabled)}>
              {job.enabled ? "禁用" : "启用"}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function HeartbeatPage() {
  const [heartbeat, setHeartbeat] = useState<any>(null);

  async function onLoad() {
    setHeartbeat(await getHeartbeat());
  }

  return (
    <section className="panel">
      <h2>Heartbeat</h2>
      <button onClick={onLoad}>刷新心跳</button>
      {heartbeat && (
        <pre className="pre">{JSON.stringify(heartbeat, null, 2)}</pre>
      )}
    </section>
  );
}

function EnvironmentsPage() {
  const [text, setText] = useState("");

  async function onLoad() {
    const envs = await listEnvVars();
    const lines = envs.map((item) => `${item.key}=${item.value}`);
    setText(lines.join("\n"));
  }

  async function onSave() {
    const vars: Record<string, string> = {};
    for (const line of text.split("\n")) {
      if (!line.trim()) continue;
      const idx = line.indexOf("=");
      if (idx <= 0) continue;
      const key = line.slice(0, idx).trim();
      const value = line.slice(idx + 1);
      vars[key] = value;
    }
    await saveEnvVars(vars);
  }

  return (
    <section className="panel">
      <h2>Environments</h2>
      <div className="row">
        <button onClick={onLoad}>加载</button>
        <button onClick={onSave}>保存</button>
      </div>
      <textarea
        value={text}
        onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
          setText(e.target.value)
        }
        rows={14}
        className="textarea"
        placeholder="OPENAI_API_KEY=..."
      />
    </section>
  );
}

function SkillsPage() {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [active, setActive] = useState<string[]>([]);

  async function onLoad() {
    setSkills(await listSkills());
    setActive(await listActiveSkills());
  }

  async function onToggle(skillName: string, isActive: boolean) {
    if (isActive) {
      await disableSkill(skillName);
    } else {
      await enableSkill(skillName);
    }
    await onLoad();
  }

  return (
    <section className="panel">
      <h2>Skills</h2>
      <button onClick={onLoad}>刷新技能</button>
      <div className="list">
        {skills.map((skill: SkillItem, idx: number) => {
          const skillName = skill.name || `skill-${idx}`;
          const isActive = active.includes(skillName);
          return (
            <div key={skillName} className="card row spread">
              <div>
                <p>
                  <strong>{skillName}</strong>
                </p>
                {skill.description && (
                  <p className="muted">{skill.description}</p>
                )}
              </div>
              <button onClick={() => onToggle(skillName, isActive)}>
                {isActive ? "禁用" : "启用"}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function McpPage() {
  const [clients, setClients] = useState<McpClientItem[]>([]);
  const [newKey, setNewKey] = useState("");
  const [newName, setNewName] = useState("");
  const [newCommand, setNewCommand] = useState("");

  async function onLoad() {
    setClients(await listMcpClients());
  }

  async function onCreate() {
    if (!newKey.trim()) return;
    await createMcpClient(newKey.trim(), {
      name: newName.trim() || newKey.trim(),
      transport: "stdio",
      enabled: true,
      description: "",
      command: newCommand.trim() || "npx",
      args: [],
      url: "",
      env: {},
    });
    setNewKey("");
    setNewName("");
    setNewCommand("");
    await onLoad();
  }

  async function onToggle(key: string) {
    await toggleMcpClient(key);
    await onLoad();
  }

  async function onDelete(key: string) {
    await deleteMcpClient(key);
    await onLoad();
  }

  return (
    <section className="panel">
      <h2>MCP</h2>
      <div className="row wrap">
        <input
          value={newKey}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setNewKey(e.target.value)
          }
          placeholder="client key"
        />
        <input
          value={newName}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setNewName(e.target.value)
          }
          placeholder="display name"
        />
        <input
          value={newCommand}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setNewCommand(e.target.value)
          }
          placeholder="command (e.g. npx)"
        />
        <button onClick={onCreate}>新增</button>
      </div>
      <button onClick={onLoad}>刷新 MCP 客户端</button>
      <div className="list">
        {clients.map((item: McpClientItem) => (
          <div key={item.key} className="card">
            <p>
              <strong>Key:</strong> {item.key}
            </p>
            <p>
              <strong>Name:</strong> {item.name || "-"}
            </p>
            <p>
              <strong>Transport:</strong> {item.transport || "-"}
            </p>
            <p>
              <strong>Enabled:</strong> {String(item.enabled ?? true)}
            </p>
            <div className="row">
              <button onClick={() => onToggle(item.key)}>
                {item.enabled ? "禁用" : "启用"}
              </button>
              <button className="danger" onClick={() => onDelete(item.key)}>
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function WorkspacePage() {
  const [workspace, setWorkspace] = useState<any>(null);
  const [profile, setProfile] = useState<{
    exists: boolean;
    content: string;
    path?: string;
  } | null>(null);

  async function onLoad() {
    setWorkspace(await getWorkspaceInfo());
    setProfile(await getWorkspaceProfile());
  }

  return (
    <section className="panel">
      <h2>Workspace</h2>
      <button onClick={onLoad}>刷新工作区</button>
      {workspace && (
        <pre className="pre">{JSON.stringify(workspace, null, 2)}</pre>
      )}
      {profile && (
        <>
          <h3>PROFILE.md</h3>
          {!profile.exists ? (
            <p className="muted">未找到 PROFILE.md</p>
          ) : (
            <pre className="pre">{profile.content}</pre>
          )}
        </>
      )}
    </section>
  );
}

function AgentConfigPage() {
  const [config, setConfig] = useState<AgentRunningConfig>({
    max_iters: 50,
    max_input_length: 128000,
  });

  async function onLoad() {
    setConfig(await getAgentRunningConfig());
  }

  async function onSave() {
    await updateAgentRunningConfig(config);
    await onLoad();
  }

  return (
    <section className="panel">
      <h2>Agent Config</h2>
      <div className="row wrap">
        <button onClick={onLoad}>加载</button>
        <button onClick={onSave}>保存</button>
      </div>
      <div className="list">
        <div className="card">
          <p>
            <strong>max_iters</strong>
          </p>
          <input
            type="number"
            value={config.max_iters}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setConfig((prev: AgentRunningConfig) => ({
                ...prev,
                max_iters: Number(e.target.value) || 1,
              }))
            }
          />
        </div>
        <div className="card">
          <p>
            <strong>max_input_length</strong>
          </p>
          <input
            type="number"
            value={config.max_input_length}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setConfig((prev: AgentRunningConfig) => ({
                ...prev,
                max_input_length: Number(e.target.value) || 1000,
              }))
            }
          />
        </div>
      </div>
    </section>
  );
}

function ModelsPage() {
  const [providers, setProviders] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);

  async function onLoad() {
    setProviders(await listProviders());
    setModels(await listAvailableModels());
  }

  return (
    <section className="panel">
      <h2>Models</h2>
      <button onClick={onLoad}>刷新模型设置</button>
      <h3>Providers</h3>
      <div className="list">
        {providers.map((provider, idx) => (
          <div key={idx} className="card">
            <p>
              <strong>{provider.name || provider.id || "-"}</strong>
            </p>
            <p>
              <strong>Type:</strong>{" "}
              {provider.provider_type || provider.type || "-"}
            </p>
            {provider.model_name && (
              <p>
                <strong>Model:</strong> {provider.model_name}
              </p>
            )}
            {provider.base_url && <p className="muted">{provider.base_url}</p>}
          </div>
        ))}
      </div>
      <h3>Available Models</h3>
      <div className="list">
        {models.map((model, idx) => (
          <div key={idx} className="card">
            <p>
              <strong>{model.name || model.model_name || "-"}</strong>
            </p>
            <p className="muted">provider: {model.provider || "-"}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <h1>ResearchClaw</h1>
          <p>Scholar Console</p>
        </div>
        <nav className="menu">
          <h4>Chat</h4>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/papers">Papers</NavLink>

          <h4>Control</h4>
          <NavLink to="/channels">Channels</NavLink>
          <NavLink to="/sessions">Sessions</NavLink>
          <NavLink to="/cron-jobs">Cron Jobs</NavLink>
          <NavLink to="/heartbeat">Heartbeat</NavLink>
          <NavLink to="/status">Status</NavLink>

          <h4>Agent</h4>
          <NavLink to="/workspace">Workspace</NavLink>
          <NavLink to="/skills">Skills</NavLink>
          <NavLink to="/mcp">MCP</NavLink>
          <NavLink to="/agent-config">Agent Config</NavLink>

          <h4>Settings</h4>
          <NavLink to="/models">Models</NavLink>
          <NavLink to="/environments">Environments</NavLink>
        </nav>
      </aside>

      <main className="content">
        <Routes>
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
