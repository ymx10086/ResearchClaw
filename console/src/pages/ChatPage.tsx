import { useMemo, useRef, useEffect, useState, useCallback } from "react";
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
import { getSessionDetail, getSessions, streamChat } from "../api";
import type { ChatMessage, SessionItem, StreamEvent, ToolCallInfo } from "../types";
import { preprocessMarkdown } from "../utils/markdown";

const CHAT_STATE_STORAGE_KEY = "researchclaw.chat.state.v1";

type PersistedChatState = {
  sessionId?: string;
  messages?: ChatMessage[];
};

function createSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `chat-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function normalizeChatRole(value: unknown): ChatMessage["role"] {
  if (value === "user" || value === "assistant" || value === "tool") {
    return value;
  }
  return "assistant";
}

function loadPersistedChatState(): PersistedChatState {
  try {
    const raw = localStorage.getItem(CHAT_STATE_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as PersistedChatState;
    if (!parsed || typeof parsed !== "object") return {};
    return {
      sessionId:
        typeof parsed.sessionId === "string" ? parsed.sessionId : undefined,
      messages: Array.isArray(parsed.messages)
        ? parsed.messages.filter(
            (m) =>
              m
              && typeof m === "object"
              && typeof (m as ChatMessage).content === "string",
          )
        : [],
    };
  } catch {
    return {};
  }
}

function formatTs(ts?: number): string {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString();
}

export default function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>(
    () => loadPersistedChatState().messages || [],
  );
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(
    () => loadPersistedChatState().sessionId,
  );
  const [chatLoading, setChatLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const hydratedSessionRef = useRef<string>("");

  // Current streaming state (for the in-progress assistant message)
  const [streamContent, setStreamContent] = useState("");
  const [streamThinking, setStreamThinking] = useState("");
  const [streamToolCalls, setStreamToolCalls] = useState<ToolCallInfo[]>([]);

  const canSend = useMemo(
    () => chatInput.trim().length > 0 && !chatLoading,
    [chatInput, chatLoading],
  );

  const querySessionId = searchParams.get("session_id") || undefined;

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
    const payload: PersistedChatState = { sessionId, messages };
    localStorage.setItem(CHAT_STATE_STORAGE_KEY, JSON.stringify(payload));
  }, [messages, sessionId]);

  useEffect(() => {
    void loadSessionList();
  }, [loadSessionList]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamContent, streamThinking, streamToolCalls]);

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
        setSessionId(targetSessionId);
        setMessages(restored);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [messages.length, querySessionId, sessionId]);

  const resetStream = useCallback(() => {
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);
  }, []);

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
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    const finalContent = streamContent || "(已停止)";
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: finalContent,
        thinking: streamThinking || undefined,
        toolCalls: streamToolCalls.length ? [...streamToolCalls] : undefined,
      },
    ]);
    resetStream();
    setChatLoading(false);
  }

  function onNewConversation() {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setChatLoading(false);
    setChatInput("");
    setMessages([]);
    setSessionId(undefined);
    hydratedSessionRef.current = "";
    resetStream();
    localStorage.removeItem(CHAT_STATE_STORAGE_KEY);
    syncQuerySession(undefined);
  }

  async function onOpenSession(targetSessionId: string) {
    if (!targetSessionId) return;
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setChatLoading(false);
      resetStream();
    }
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
      setSessionId(targetSessionId);
      hydratedSessionRef.current = targetSessionId;
      setMessages(restored);
    } catch {
      // Ignore and keep current UI state.
    }
  }

  function onSendChat() {
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    const activeSessionId = sessionId || createSessionId();
    if (!sessionId) {
      setSessionId(activeSessionId);
      hydratedSessionRef.current = activeSessionId;
      syncQuerySession(activeSessionId);
    }

    setChatLoading(true);
    resetStream();
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setChatInput("");

    let accContent = "";
    let accThinking = "";
    let accToolCalls: ToolCallInfo[] = [];

    const controller = streamChat(text, activeSessionId, (event: StreamEvent) => {
      if (event.session_id) {
        setSessionId(event.session_id);
        hydratedSessionRef.current = event.session_id;
        if (searchParams.get("session_id") !== event.session_id) {
          syncQuerySession(event.session_id);
        }
      }

      switch (event.type) {
        case "thinking":
          accThinking += event.content || "";
          setStreamThinking(accThinking);
          break;

        case "content":
          accContent += event.content || "";
          setStreamContent(accContent);
          break;

        case "content_replace":
          accContent = event.content || "";
          setStreamContent(accContent);
          break;

        case "tool_call":
          accToolCalls = [
            ...accToolCalls,
            {
              name: event.name || "unknown",
              arguments: event.arguments,
              status: "running",
            },
          ];
          setStreamToolCalls([...accToolCalls]);
          break;

        case "tool_result": {
          const idx = accToolCalls.findIndex(
            (tc) => tc.name === event.name && tc.status === "running",
          );
          if (idx !== -1) {
            accToolCalls[idx] = {
              ...accToolCalls[idx],
              result: event.result,
              status: "done",
            };
          } else {
            accToolCalls.push({
              name: event.name || "unknown",
              result: event.result,
              status: "done",
            });
          }
          setStreamToolCalls([...accToolCalls]);
          break;
        }

        case "done": {
          const finalContent = event.content || accContent;
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: finalContent,
              thinking: accThinking || undefined,
              toolCalls: accToolCalls.length ? accToolCalls : undefined,
            },
          ]);
          resetStream();
          setChatLoading(false);
          abortRef.current = null;
          void loadSessionList();
          break;
        }

        case "error": {
          const errText = String(event.content || "unknown error");
          const mergedContent = accContent.trim()
            ? `${accContent}\n\n[流式中断] ${errText}`
            : `错误: ${errText}`;
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: mergedContent,
              thinking: accThinking || undefined,
              toolCalls: accToolCalls.length ? accToolCalls : undefined,
            },
          ]);
          resetStream();
          setChatLoading(false);
          abortRef.current = null;
          void loadSessionList();
          break;
        }
      }
    });

    abortRef.current = controller;
  }

  return (
    <div className="panel chat-layout">
      <aside className="chat-history-panel">
        <div className="chat-history-header">
          <button className="btn-secondary btn-sm" onClick={onNewConversation}>
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
                {formatTs(session.updated_at)} · {session.message_count ?? 0} 条
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
          <button className="btn-secondary btn-sm" onClick={onNewConversation}>
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
                将为你提供专业帮助。
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`msg ${msg.role}`}>
              <div className="msg-avatar">{msg.role === "user" ? "你" : "S"}</div>
              <div className="msg-bubble">
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

        <div className="chat-input-bar">
          <input
            value={chatInput}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setChatInput(e.target.value)
            }
            placeholder="例如：帮我总结 Diffusion Models 近两年趋势..."
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
