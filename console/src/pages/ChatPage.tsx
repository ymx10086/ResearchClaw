import {
  useMemo,
  useRef,
  useEffect,
  useState,
  useCallback,
  useSyncExternalStore,
} from "react";
import type { ChangeEvent, KeyboardEvent } from "react";
import {
  MessageSquare,
  Send,
  Loader2,
  BrainCircuit,
  Wrench,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Square,
  PlusCircle,
  RefreshCw,
} from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSearchParams } from "react-router-dom";
import { getSessionDetail, getSessions } from "../api";
import type { ChatMessage, SessionItem, ToolCallInfo } from "../types";
import { preprocessMarkdown } from "../utils/markdown";
import { MetricPill, PageHeader } from "../components/ui";
import {
  getChatRuntimeState,
  replaceChatConversation,
  sendChatMessage,
  startNewConversation,
  stopChatStreaming,
  subscribeChatRuntime,
} from "../chatRuntime";

function normalizeChatRole(value: unknown): ChatMessage["role"] {
  if (value === "user" || value === "assistant" || value === "tool") {
    return value;
  }
  return "assistant";
}

function formatTs(ts?: number): string {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString();
}

export default function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const chatState = useSyncExternalStore(
    subscribeChatRuntime,
    getChatRuntimeState,
    getChatRuntimeState,
  );
  const {
    messages,
    sessionId,
    chatLoading,
    streamContent,
    streamThinking,
    streamToolCalls,
  } = chatState;
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hydratedSessionRef = useRef<string>("");

  const canSend = useMemo(
    () => chatInput.trim().length > 0 && !chatLoading,
    [chatInput, chatLoading],
  );

  const querySessionId = searchParams.get("session_id") || undefined;
  const latestSession = sessions[0];

  const loadSessionList = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const list = await getSessions();
      setSessions(Array.isArray(list) ? list : []);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSessionList();
  }, [loadSessionList]);

  const prevLoadingRef = useRef(chatLoading);
  useEffect(() => {
    if (prevLoadingRef.current && !chatLoading) {
      void loadSessionList();
    }
    prevLoadingRef.current = chatLoading;
  }, [chatLoading, loadSessionList]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamContent, streamThinking, streamToolCalls]);

  useEffect(() => {
    if (!sessionId) return;
    if (querySessionId === sessionId) return;
    syncQuerySession(sessionId);
    // Keep URL and active session aligned while ChatPage is mounted.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, querySessionId]);

  useEffect(() => {
    const targetSessionId = querySessionId || sessionId;
    if (!targetSessionId) return;
    if (querySessionId && querySessionId === sessionId && messages.length > 0) {
      return;
    }
    // Keep in-memory messages while navigating tabs; only hydrate when needed.
    if (!querySessionId && messages.length > 0) return;
    if (targetSessionId === hydratedSessionRef.current) return;
    hydratedSessionRef.current = targetSessionId;

    let cancelled = false;
    void getSessionDetail(targetSessionId)
      .then((detail) => {
        if (cancelled) return;
        const sessionMessages = Array.isArray(detail?.messages)
          ? detail.messages
          : [];
        const restored: ChatMessage[] = sessionMessages.map((m: any) => ({
          role: normalizeChatRole(m?.role),
          content: String(m?.content ?? ""),
        }));
        replaceChatConversation(targetSessionId, restored, {
          stopStreaming: false,
        });
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [messages.length, querySessionId, sessionId]);

  function syncQuerySession(nextSessionId?: string) {
    const next = new URLSearchParams(searchParams);
    if (nextSessionId) {
      next.set("session_id", nextSessionId);
    } else {
      next.delete("session_id");
    }
    setSearchParams(next, { replace: true });
  }

  function handleStop() {
    stopChatStreaming();
  }

  function onNewConversation() {
    startNewConversation();
    setChatInput("");
    hydratedSessionRef.current = "";
    syncQuerySession(undefined);
  }

  async function onOpenSession(targetSessionId: string) {
    if (!targetSessionId) return;
    if (chatLoading) stopChatStreaming();
    syncQuerySession(targetSessionId);
    if (targetSessionId === sessionId && messages.length > 0) return;
    try {
      const detail = await getSessionDetail(targetSessionId);
      const sessionMessages = Array.isArray(detail?.messages)
        ? detail.messages
        : [];
      const restored: ChatMessage[] = sessionMessages.map((m: any) => ({
        role: normalizeChatRole(m?.role),
        content: String(m?.content ?? ""),
      }));
      hydratedSessionRef.current = targetSessionId;
      replaceChatConversation(targetSessionId, restored);
    } catch {
      // Ignore and keep current UI state.
    }
  }

  function onSendChat() {
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    const activeSessionId = sendChatMessage(text, {
      preferredSessionId: sessionId,
    });
    if (!activeSessionId) return;
    hydratedSessionRef.current = activeSessionId;
    if (searchParams.get("session_id") !== activeSessionId) {
      syncQuerySession(activeSessionId);
    }
    setChatInput("");
  }

  function usePrompt(prompt: string) {
    setChatInput(prompt);
  }

  return (
    <div className="panel">
      <PageHeader
        eyebrow="Research Workflow"
        title="AI 对话"
        description="把论文检索、摘要归纳、实验设计和写作修改放进同一条研究线程，减少上下文切换。"
        meta={
          <div className="page-header-meta-row">
            <MetricPill label="历史会话" value={sessions.length} />
            <MetricPill
              label="当前模式"
              value={chatLoading ? "推理中" : "可交互"}
            />
            <MetricPill
              label="最近更新"
              value={latestSession ? formatTs(latestSession.updated_at) : "-"}
            />
          </div>
        }
      />

      <div className="chat-layout">
        <aside className="chat-history-panel">
          <div className="chat-history-summary">
            <span className="chat-history-kicker">Conversation Hub</span>
            <h3>研究线程</h3>
            <p>保留连续上下文，随时回到某条会话继续推进。</p>
          </div>

          <div className="chat-history-header">
            <button
              className="btn-secondary btn-sm"
              onClick={onNewConversation}
            >
              <PlusCircle size={14} />
              新对话
            </button>
            <button
              className="btn-ghost btn-sm"
              onClick={() => void loadSessionList()}
              disabled={sessionsLoading}
            >
              <RefreshCw
                size={14}
                className={sessionsLoading ? "spin-icon" : undefined}
              />
              刷新
            </button>
          </div>

          <div className="chat-history-list">
            {sessions.length === 0 && (
              <div className="chat-history-empty">暂无历史会话</div>
            )}
            {sessions.map((session) => (
              <button
                key={session.session_id}
                className={`chat-history-item${
                  session.session_id === sessionId ? " active" : ""
                }`}
                onClick={() => void onOpenSession(session.session_id)}
              >
                <div className="chat-history-title">
                  {session.title || session.session_id}
                </div>
                <div className="chat-history-meta">
                  {formatTs(session.updated_at)} · {session.message_count ?? 0}{" "}
                  条
                </div>
              </button>
            ))}
          </div>
        </aside>

        <div className="chat-container">
          <div className="chat-toolbar">
            <div className="chat-toolbar-session">
              当前会话: {sessionId || "未创建"}
            </div>
            <button
              className="btn-secondary btn-sm"
              onClick={onNewConversation}
            >
              <PlusCircle size={14} />
              新对话
            </button>
          </div>

          <div className="messages">
            {messages.length === 0 && !chatLoading && (
              <div className="chat-empty">
                <div className="chat-empty-icon">
                  <MessageSquare size={28} />
                </div>
                <h3>开始一段研究对话</h3>
                <p>
                  你可以询问文献综述、实验设计、论文写作、数据分析等任何学术问题。Scholar
                  会把回答、思考过程和工具调用留在同一个线程中。
                </p>
                <div className="chat-suggestion-row">
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() =>
                      usePrompt(
                        "帮我梳理多智能体科研助手近两年的产品趋势和差异",
                      )
                    }
                  >
                    趋势梳理
                  </button>
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() =>
                      usePrompt("给我做一个关于 RAG 论文的 related work 提纲")
                    }
                  >
                    Related Work
                  </button>
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() =>
                      usePrompt("基于这篇论文，给出可复现实验计划和指标表")
                    }
                  >
                    实验计划
                  </button>
                </div>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div key={idx} className={`msg ${msg.role}`}>
                <div className="msg-avatar">
                  {msg.role === "user" ? "你" : "S"}
                </div>
                <div className="msg-bubble">
                  <div className="msg-role-label">
                    {msg.role === "user" ? "Researcher" : "Scholar"}
                  </div>
                  {msg.thinking && <ThinkingBlock content={msg.thinking} />}
                  {msg.toolCalls && <ToolCallsBlock calls={msg.toolCalls} />}
                  <MessageContent content={msg.content} />
                </div>
              </div>
            ))}

            {chatLoading && (
              <div className="msg assistant">
                <div className="msg-avatar">S</div>
                <div className="msg-bubble">
                  <div className="msg-role-label">Scholar</div>
                  {streamThinking && (
                    <ThinkingBlock content={streamThinking} streaming />
                  )}
                  {streamToolCalls.length > 0 && (
                    <ToolCallsBlock calls={streamToolCalls} />
                  )}
                  {streamContent ? (
                    <MessageContent content={streamContent} />
                  ) : (
                    !streamThinking &&
                    streamToolCalls.length === 0 && (
                      <span className="stream-cursor">
                        <Loader2 size={14} className="spinner" />
                      </span>
                    )
                  )}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-composer-shell">
            <div className="chat-composer-hint">
              支持连续追问；如果需要切换主题，建议新建对话保持上下文干净。
            </div>
            <div className="chat-input-bar">
              <input
                value={chatInput}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setChatInput(e.target.value)
                }
                placeholder="例如：帮我总结 Diffusion Models 近两年趋势，并给出可引用的研究脉络..."
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === "Enter" && canSend) onSendChat();
                }}
              />
              {chatLoading ? (
                <button onClick={handleStop} className="btn-stop">
                  <Square size={14} />
                  停止
                </button>
              ) : (
                <button onClick={onSendChat} disabled={!canSend}>
                  <Send size={16} />
                  发送
                </button>
              )}
            </div>
          </div>

          {sessionId && (
            <div className="chat-session-label">
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "var(--success)",
                  display: "inline-block",
                }}
              />
              Session: {sessionId}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageContent({ content }: { content: string }) {
  if (!content) return null;
  const normalized = preprocessMarkdown(content);
  return (
    <div className="msg-text markdown-body">
      <Markdown remarkPlugins={[remarkGfm]}>{normalized}</Markdown>
    </div>
  );
}

function ThinkingBlock({
  content,
  streaming,
}: {
  content: string;
  streaming?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="thinking-block">
      <div className="thinking-header" onClick={() => setExpanded((v) => !v)}>
        <BrainCircuit size={14} />
        <span>{streaming ? "正在思考..." : "思考过程"}</span>
        {streaming && <Loader2 size={12} className="spinner" />}
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </div>
      {expanded && <div className="thinking-content">{content}</div>}
    </div>
  );
}

function ToolCallsBlock({ calls }: { calls: ToolCallInfo[] }) {
  return (
    <div className="tool-calls-block">
      {calls.map((tc, i) => (
        <div
          key={i}
          className={`tool-call-item tool-call-${tc.status || "running"}`}
        >
          <div className="tool-call-header">
            {tc.status === "running" ? (
              <Loader2 size={13} className="spinner" />
            ) : tc.status === "error" ? (
              <XCircle size={13} />
            ) : (
              <CheckCircle2 size={13} />
            )}
            <Wrench size={12} />
            <span className="tool-call-name">{tc.name}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
