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
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { useSearchParams } from "react-router-dom";
import { getSessionDetail, getSessions } from "../api";
import { useI18n } from "../i18n";
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
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const chatState = useSyncExternalStore(
    subscribeChatRuntime,
    getChatRuntimeState,
    getChatRuntimeState,
  );
  const {
    messages,
    sessionId,
    agentId,
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
  const openingSessionRef = useRef<string>("");

  const canSend = useMemo(
    () => chatInput.trim().length > 0 && !chatLoading,
    [chatInput, chatLoading],
  );

  const querySessionId = searchParams.get("session_id") || undefined;
  const queryAgentId = searchParams.get("agent_id") || undefined;
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
    syncQuerySession(sessionId, agentId);
    // Keep URL and active session aligned while ChatPage is mounted.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, querySessionId, sessionId]);

  useEffect(() => {
    const targetSessionId = querySessionId || sessionId;
    const targetAgentId = queryAgentId || agentId;
    if (!targetSessionId) return;
    if (querySessionId && querySessionId === sessionId && messages.length > 0) {
      return;
    }
    // Keep in-memory messages while navigating tabs; only hydrate when needed.
    if (!querySessionId && messages.length > 0) return;
    const hydrationKey = `${targetAgentId || "main"}:${targetSessionId}`;
    if (hydrationKey === hydratedSessionRef.current) return;
    if (hydrationKey === openingSessionRef.current) return;
    hydratedSessionRef.current = hydrationKey;

    let cancelled = false;
    void getSessionDetail(targetSessionId, targetAgentId)
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
          agentId: detail?.agent_id || targetAgentId,
          stopStreaming: false,
        });
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [agentId, messages.length, queryAgentId, querySessionId, sessionId]);

  function syncQuerySession(nextSessionId?: string, nextAgentId?: string) {
    const next = new URLSearchParams(searchParams);
    if (nextSessionId) {
      next.set("session_id", nextSessionId);
    } else {
      next.delete("session_id");
    }
    if (nextAgentId) {
      next.set("agent_id", nextAgentId);
    } else {
      next.delete("agent_id");
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
    syncQuerySession(undefined, undefined);
  }

  async function onOpenSession(
    targetSessionId: string,
    targetAgentId?: string,
  ) {
    if (!targetSessionId) return;
    const requestedAgentId = targetAgentId || undefined;
    const targetKey = `${requestedAgentId || "main"}:${targetSessionId}`;
    if (openingSessionRef.current === targetKey) return;
    if (
      targetSessionId === sessionId &&
      (requestedAgentId || "main") === (agentId || "main") &&
      messages.length > 0
    ) {
      syncQuerySession(targetSessionId, requestedAgentId);
      return;
    }

    openingSessionRef.current = targetKey;
    hydratedSessionRef.current = targetKey;
    if (chatLoading) stopChatStreaming();
    try {
      const detail = await getSessionDetail(targetSessionId, requestedAgentId);
      const sessionMessages = Array.isArray(detail?.messages)
        ? detail.messages
        : [];
      const restored: ChatMessage[] = sessionMessages.map((m: any) => ({
        role: normalizeChatRole(m?.role),
        content: String(m?.content ?? ""),
      }));
      const resolvedAgentId = detail?.agent_id || requestedAgentId;
      hydratedSessionRef.current = `${
        resolvedAgentId || "main"
      }:${targetSessionId}`;
      replaceChatConversation(targetSessionId, restored, {
        agentId: resolvedAgentId,
      });
      syncQuerySession(targetSessionId, resolvedAgentId);
    } catch {
      // Ignore and keep current UI state.
    } finally {
      if (openingSessionRef.current === targetKey) {
        openingSessionRef.current = "";
      }
    }
  }

  function onSendChat() {
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    const activeSessionId = sendChatMessage(text, {
      preferredAgentId: queryAgentId || agentId,
      preferredSessionId: sessionId,
    });
    if (!activeSessionId) return;
    hydratedSessionRef.current = `${
      queryAgentId || agentId || "main"
    }:${activeSessionId}`;
    if (searchParams.get("session_id") !== activeSessionId) {
      syncQuerySession(activeSessionId, queryAgentId || agentId);
    }
    setChatInput("");
  }

  function usePrompt(prompt: string) {
    setChatInput(prompt);
  }

  return (
    <div className="panel chat-page-shell">
      <PageHeader
        title={t("AI 对话")}
        meta={
          <div className="page-header-meta-row">
            <MetricPill label={t("历史会话")} value={sessions.length} />
            <MetricPill
              label={t("当前模式")}
              value={chatLoading ? t("推理中") : t("可交互")}
            />
            <MetricPill
              label={t("最近更新")}
              value={latestSession ? formatTs(latestSession.updated_at) : "-"}
            />
          </div>
        }
      />

      <div className="chat-layout">
        <aside className="chat-history-panel">
          <div className="chat-history-summary">
            <h3>{t("研究线程")}</h3>
          </div>

          <div className="chat-history-header">
            <button
              className="btn-secondary btn-sm"
              onClick={onNewConversation}
            >
              <PlusCircle size={14} />
              {t("新对话")}
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
              {t("刷新")}
            </button>
          </div>

          <div className="chat-history-list">
            {sessions.length === 0 && (
              <div className="chat-history-empty">{t("暂无历史会话")}</div>
            )}
            {sessions.map((session) => (
              <button
                key={session.session_id}
                className={`chat-history-item${
                  session.session_id === sessionId ? " active" : ""
                }`}
                onClick={() =>
                  void onOpenSession(
                    session.session_id,
                    session.agent_id || undefined,
                  )
                }
              >
                <div className="chat-history-title">
                  {session.title || session.session_id}
                </div>
                <div className="chat-history-meta">
                  {formatTs(session.updated_at)} ·{" "}
                  {t("{count} 条", { count: session.message_count ?? 0 })}
                </div>
              </button>
            ))}
          </div>
        </aside>

        <div className="chat-container">
          <div className="chat-toolbar">
            <div className="chat-toolbar-session">
              {t("当前会话: ")}
              {sessionId || t("未创建")}
            </div>
            <button
              className="btn-secondary btn-sm"
              onClick={onNewConversation}
            >
              <PlusCircle size={14} />
              {t("新对话")}
            </button>
          </div>

          <div className="messages">
            {messages.length === 0 && !chatLoading && (
              <div className="chat-empty">
                <div className="chat-empty-icon">
                  <MessageSquare size={28} />
                </div>
                <h3>{t("开始一段研究对话")}</h3>
                <div className="chat-suggestion-row">
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() =>
                      usePrompt(
                        "帮我梳理多智能体科研助手近两年的产品趋势和差异",
                      )
                    }
                  >
                    {t("趋势梳理")}
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
                    {t("实验计划")}
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
            <div className="chat-composer-meta">
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
                  {t("停止")}
                </button>
              ) : (
                <button onClick={onSendChat} disabled={!canSend}>
                  <Send size={16} />
                  {t("发送")}
                </button>
              )}
            </div>
          </div>
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
      <Markdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {normalized}
      </Markdown>
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
