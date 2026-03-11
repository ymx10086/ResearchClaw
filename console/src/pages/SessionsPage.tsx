import { useEffect, useState } from "react";
import {
  MessageCircle,
  RefreshCw,
  Eye,
  Trash2,
  Clock,
  Hash,
  PlayCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  getAgents,
  getSessionsByAgent,
  getSessionDetail,
  deleteSession,
} from "../api";
import type { SessionItem } from "../types";
import { PageHeader, EmptyState, Badge, DetailModal } from "../components/ui";

function formatTs(ts?: number): string {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString();
}

export default function SessionsPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [activeAgent, setActiveAgent] = useState<string>("all");
  const [selected, setSelected] = useState<any>(null);
  const [loaded, setLoaded] = useState(false);

  async function onLoad() {
    const [sessionRows, agentRows] = await Promise.all([
      getSessionsByAgent(activeAgent === "all" ? undefined : activeAgent),
      getAgents(),
    ]);
    setSessions(sessionRows);
    setAgents(agentRows);
    setLoaded(true);
  }

  useEffect(() => {
    void onLoad();
  }, [activeAgent]);

  async function onOpen(sessionId: string) {
    setSelected(
      await getSessionDetail(
        sessionId,
        activeAgent === "all" ? undefined : activeAgent,
      ),
    );
  }

  async function onDelete(sessionId: string) {
    await deleteSession(
      sessionId,
      activeAgent === "all" ? undefined : activeAgent,
    );
    if (selected?.session_id === sessionId) {
      setSelected(null);
    }
    await onLoad();
  }

  function onContinue(sessionId: string) {
    navigate(`/chat?session_id=${encodeURIComponent(sessionId)}`);
  }

  return (
    <div className="panel">
      <PageHeader
        title="会话管理"
        description="管理 Agent 交互会话记录"
        actions={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select
              value={activeAgent}
              onChange={(e) => setActiveAgent(e.target.value)}
            >
              <option value="all">全部 Agent</option>
              {agents.map((agent) => (
                <option key={String(agent.id)} value={String(agent.id)}>
                  {String(agent.id)}
                </option>
              ))}
            </select>
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              刷新会话
            </button>
          </div>
        }
      />

      {!loaded && sessions.length === 0 && (
        <EmptyState
          icon={<MessageCircle size={28} />}
          title="加载会话列表"
          description="查看和管理所有 Agent 交互会话"
          action={
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              加载
            </button>
          }
        />
      )}

      <div className="card-list animate-list">
        {sessions.map((session: SessionItem) => (
          <div key={session.session_id} className="data-row">
            <div className="data-row-info">
              <div className="data-row-title">
                {session.title || session.session_id}
              </div>
              <div className="data-row-meta">
                <Clock
                  size={11}
                  style={{ marginRight: 3, verticalAlign: "middle" }}
                />
                {formatTs(session.updated_at)}
                <span style={{ margin: "0 6px" }}>·</span>
                <Hash
                  size={11}
                  style={{ marginRight: 2, verticalAlign: "middle" }}
                />
                {session.message_count ?? 0} 条消息
              </div>
            </div>
            <div className="data-row-actions">
              <Badge variant="neutral">
                {(session.agent_id || "main") +
                  ":" +
                  session.session_id.slice(0, 8)}
              </Badge>
              <button
                className="btn-sm btn-secondary"
                onClick={() => onOpen(session.session_id)}
              >
                <Eye size={14} />
                查看
              </button>
              <button
                className="btn-sm"
                onClick={() => onContinue(session.session_id)}
              >
                <PlayCircle size={14} />
                继续对话
              </button>
              <button
                className="btn-sm danger"
                onClick={() => onDelete(session.session_id)}
              >
                <Trash2 size={14} />
                删除
              </button>
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <DetailModal title="会话详情" onClose={() => setSelected(null)}>
          <pre className="pre">{JSON.stringify(selected, null, 2)}</pre>
        </DetailModal>
      )}
    </div>
  );
}
