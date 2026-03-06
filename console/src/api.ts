import type {
  AgentRunningConfig,
  ChannelItem,
  ChatMessage,
  CronJobItem,
  EnvItem,
  McpClientItem,
  PaperItem,
  ProviderItem,
  PushMessage,
  SessionItem,
  SkillItem,
  StreamEvent,
  WorkspaceFileContent,
  WorkspaceFileItem,
} from "./types";

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function sendChat(
  message: string,
  sessionId?: string,
): Promise<{ response: string; session_id: string }> {
  const res = await fetch("/api/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}

export async function searchArxiv(
  query: string,
  maxResults = 8,
): Promise<PaperItem[]> {
  const res = await fetch("/api/papers/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, source: "arxiv", max_results: maxResults }),
  });
  if (!res.ok) throw new Error("Paper search failed");
  const data = await res.json();
  if (Array.isArray(data.results)) return data.results;
  return [];
}

export async function getStatus(): Promise<{
  running: boolean;
  agent_name: string;
  tool_count: number;
}> {
  const res = await fetch("/api/agent/status");
  if (!res.ok) throw new Error("Status request failed");
  return res.json();
}

export async function getControlStatus(): Promise<any> {
  const res = await fetch("/api/control/status");
  if (!res.ok) throw new Error("Control status request failed");
  return res.json();
}

function normalizeCronJob(job: any): CronJobItem {
  const task_type = job?.task_type === "text" ? "text" : "agent";
  const mode: "stream" | "final" =
    job?.dispatch?.mode === "stream" ? "stream" : "final";
  const schedule = {
    type: "cron" as const,
    cron: String(job?.schedule?.cron ?? ""),
    timezone: String(job?.schedule?.timezone ?? "UTC"),
  };
  const dispatch: CronJobItem["dispatch"] = {
    type: "channel" as const,
    channel: String(job?.dispatch?.channel ?? "console"),
    target: {
      user_id: String(job?.dispatch?.target?.user_id ?? "main"),
      session_id: String(job?.dispatch?.target?.session_id ?? "main"),
    },
    mode,
    meta:
      job?.dispatch?.meta && typeof job.dispatch.meta === "object"
        ? (job.dispatch.meta as Record<string, unknown>)
        : {},
  };
  const runtime: CronJobItem["runtime"] = {
    max_concurrency: Number(job?.runtime?.max_concurrency ?? 1),
    timeout_seconds: Number(job?.runtime?.timeout_seconds ?? 120),
    misfire_grace_seconds: Number(job?.runtime?.misfire_grace_seconds ?? 60),
  };

  return {
    id: String(job?.id ?? ""),
    name: String(job?.name ?? ""),
    enabled: Boolean(job?.enabled ?? true),
    task_type,
    cron: schedule.cron,
    timezone: schedule.timezone,
    channel: dispatch.channel,
    target_user_id: dispatch.target.user_id,
    target_session_id: dispatch.target.session_id,
    mode,
    text: typeof job?.text === "string" ? job.text : null,
    request:
      job?.request
      && typeof job.request === "object"
      && "input" in (job.request as Record<string, unknown>)
        ? (job.request as CronJobItem["request"])
        : null,
    schedule,
    dispatch,
    runtime,
    meta:
      job?.meta && typeof job.meta === "object"
        ? (job.meta as Record<string, unknown>)
        : {},
  };
}

function toCronJobPayload(job: CronJobItem): Record<string, unknown> {
  return {
    id: job.id,
    name: job.name,
    enabled: job.enabled,
    schedule: {
      type: "cron",
      cron: job.schedule.cron,
      timezone: job.schedule.timezone,
    },
    task_type: job.task_type,
    text: job.text ?? null,
    request: job.request ?? null,
    dispatch: {
      type: "channel",
      channel: job.dispatch.channel,
      target: {
        user_id: job.dispatch.target.user_id,
        session_id: job.dispatch.target.session_id,
      },
      mode: job.dispatch.mode,
      meta: job.dispatch.meta ?? {},
    },
    runtime: {
      max_concurrency: job.runtime.max_concurrency,
      timeout_seconds: job.runtime.timeout_seconds,
      misfire_grace_seconds: job.runtime.misfire_grace_seconds,
    },
    meta: job.meta ?? {},
  };
}

export async function getCronJobs(): Promise<CronJobItem[]> {
  const res = await fetch("/api/crons/cron/jobs");
  if (!res.ok) throw new Error("Cron jobs request failed");
  const data = await res.json();
  if (!Array.isArray(data)) return [];
  return data.map((job: any) => normalizeCronJob(job));
}

export async function createCronJob(job: CronJobItem): Promise<CronJobItem> {
  const res = await fetch("/api/crons/cron/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toCronJobPayload(job)),
  });
  if (!res.ok) throw new Error("Create cron job failed");
  const data = await res.json();
  return normalizeCronJob(data);
}

export async function replaceCronJob(
  jobId: string,
  job: CronJobItem,
): Promise<CronJobItem> {
  const res = await fetch(`/api/crons/cron/jobs/${encodeURIComponent(jobId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toCronJobPayload(job)),
  });
  if (!res.ok) throw new Error("Update cron job failed");
  const data = await res.json();
  return normalizeCronJob(data);
}

export async function deleteCronJob(jobId: string): Promise<void> {
  const res = await fetch(`/api/crons/cron/jobs/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Delete cron job failed");
}

export async function getChannels(): Promise<ChannelItem[]> {
  const res = await fetch("/api/control/channels");
  if (!res.ok) throw new Error("Channels request failed");
  return res.json();
}

export async function getSessions(): Promise<SessionItem[]> {
  const res = await fetch("/api/control/sessions");
  if (!res.ok) throw new Error("Sessions request failed");
  return res.json();
}

export async function getSessionDetail(sessionId: string): Promise<any> {
  const res = await fetch(
    `/api/control/sessions/${encodeURIComponent(sessionId)}`,
  );
  if (!res.ok) throw new Error("Session detail request failed");
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(
    `/api/control/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "DELETE",
    },
  );
  if (!res.ok) throw new Error("Delete session failed");
}

export async function toggleCronJob(
  jobId: string,
  enabled: boolean,
): Promise<void> {
  const action = enabled ? "resume" : "pause";
  const res = await fetch(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}/${action}`,
    {
      method: "POST",
    },
  );
  if (!res.ok) throw new Error("Toggle cron job failed");
}

export async function runCronJobNow(jobId: string): Promise<void> {
  const res = await fetch(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}/run`,
    {
      method: "POST",
    },
  );
  if (!res.ok) throw new Error("Run cron job failed");
}

export async function getConsolePushMessages(
  sessionId?: string,
): Promise<PushMessage[]> {
  const path = sessionId
    ? `/api/console/push-messages?session_id=${encodeURIComponent(sessionId)}`
    : "/api/console/push-messages";
  const res = await fetch(path);
  if (!res.ok) throw new Error("Get console push messages failed");
  const data = await res.json();
  if (!Array.isArray(data?.messages)) return [];
  return data.messages
    .map((item: any) => ({
      id: String(item?.id ?? ""),
      text: String(item?.text ?? ""),
    }))
    .filter((item: PushMessage) => item.id && item.text);
}

export async function getHeartbeat(): Promise<any> {
  const res = await fetch("/api/control/heartbeat");
  if (!res.ok) throw new Error("Heartbeat request failed");
  return res.json();
}

export async function listEnvVars(): Promise<EnvItem[]> {
  const res = await fetch("/api/envs");
  if (!res.ok) throw new Error("List envs failed");
  return res.json();
}

export async function saveEnvVars(vars: Record<string, string>): Promise<void> {
  const res = await fetch("/api/envs", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(vars),
  });
  if (!res.ok) throw new Error("Save envs failed");
}

export async function listMcpClients(): Promise<McpClientItem[]> {
  const res = await fetch("/api/mcp");
  if (!res.ok) throw new Error("List MCP clients failed");
  return res.json();
}

export async function createMcpClient(
  key: string,
  body: Omit<McpClientItem, "key">,
): Promise<void> {
  const res = await fetch(`/api/mcp?client_key=${encodeURIComponent(key)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Create MCP client failed");
}

export async function updateMcpClient(
  key: string,
  body: Omit<McpClientItem, "key">,
): Promise<void> {
  const res = await fetch(`/api/mcp/${encodeURIComponent(key)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Update MCP client failed");
}

export async function toggleMcpClient(key: string): Promise<void> {
  const res = await fetch(`/api/mcp/${encodeURIComponent(key)}/toggle`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error("Toggle MCP client failed");
}

export async function deleteMcpClient(key: string): Promise<void> {
  const res = await fetch(`/api/mcp/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Delete MCP client failed");
}

export async function getWorkspaceInfo(): Promise<any> {
  const res = await fetch("/api/workspace");
  if (!res.ok) throw new Error("Workspace info failed");
  return res.json();
}

export async function getWorkspaceProfile(): Promise<{
  exists: boolean;
  content: string;
  path?: string;
}> {
  const res = await fetch("/api/workspace/profile");
  if (!res.ok) throw new Error("Workspace profile failed");
  return res.json();
}

export async function listWorkspaceFiles(): Promise<WorkspaceFileItem[]> {
  const res = await fetch("/api/workspace/files");
  if (!res.ok) throw new Error("Workspace files request failed");
  const data = await res.json();
  return Array.isArray(data?.files) ? data.files : [];
}

export async function getWorkspaceRelations(): Promise<any> {
  const res = await fetch("/api/workspace/relations");
  if (!res.ok) throw new Error("Workspace relations request failed");
  return res.json();
}

export async function getWorkspaceFileContent(
  path: string,
): Promise<WorkspaceFileContent> {
  const res = await fetch(
    `/api/workspace/file?path=${encodeURIComponent(path)}`,
  );
  if (!res.ok) throw new Error("Workspace file read failed");
  return res.json();
}

export async function saveWorkspaceFileContent(
  path: string,
  content: string,
): Promise<void> {
  const res = await fetch("/api/workspace/file", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  if (!res.ok) throw new Error("Workspace file save failed");
}

export async function listSkills(): Promise<SkillItem[]> {
  const res = await fetch("/api/skills");
  if (!res.ok) throw new Error("List skills failed");
  const data = await res.json();
  return Array.isArray(data.skills) ? data.skills : [];
}

export async function listActiveSkills(): Promise<string[]> {
  const res = await fetch("/api/skills/active");
  if (!res.ok) throw new Error("List active skills failed");
  const data = await res.json();
  return Array.isArray(data.active_skills) ? data.active_skills : [];
}

export async function enableSkill(skillName: string): Promise<void> {
  const res = await fetch("/api/skills/enable", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ skill_name: skillName }),
  });
  if (!res.ok) throw new Error("Enable skill failed");
}

export async function disableSkill(skillName: string): Promise<void> {
  const res = await fetch("/api/skills/disable", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ skill_name: skillName }),
  });
  if (!res.ok) throw new Error("Disable skill failed");
}

export async function getAgentRunningConfig(): Promise<AgentRunningConfig> {
  const res = await fetch("/api/agent/running-config");
  if (!res.ok) throw new Error("Get agent config failed");
  return res.json();
}

export async function updateAgentRunningConfig(
  config: AgentRunningConfig,
): Promise<AgentRunningConfig> {
  const res = await fetch("/api/agent/running-config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Update agent config failed");
  return res.json();
}

export async function listProviders(): Promise<ProviderItem[]> {
  const res = await fetch("/api/providers");
  if (!res.ok) throw new Error("List providers failed");
  const data = await res.json();
  return Array.isArray(data.providers) ? data.providers : [];
}

export async function createProvider(provider: ProviderItem): Promise<void> {
  const res = await fetch("/api/providers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(provider),
  });
  if (!res.ok) throw new Error("Create provider failed");
}

export async function updateProvider(
  name: string,
  settings: Partial<Omit<ProviderItem, "name" | "enabled">>,
): Promise<void> {
  const res = await fetch(
    `/api/providers/${encodeURIComponent(name)}/settings`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    },
  );
  if (!res.ok) throw new Error("Update provider failed");
}

export async function setProviderEnabled(
  name: string,
  enabled: boolean,
): Promise<void> {
  const action = enabled ? "enable" : "disable";
  const res = await fetch(
    `/api/providers/${encodeURIComponent(name)}/${action}`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error("Set provider enabled failed");
}

export async function applyProvider(name: string): Promise<void> {
  const res = await fetch(`/api/providers/${encodeURIComponent(name)}/apply`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Apply provider failed");
}

export async function deleteProvider(name: string): Promise<void> {
  const res = await fetch(`/api/providers/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Delete provider failed");
}

export async function listAvailableModels(): Promise<any[]> {
  const res = await fetch("/api/providers/models");
  if (!res.ok) throw new Error("List models failed");
  const data = await res.json();
  return Array.isArray(data.models) ? data.models : [];
}

export function appendMessage(
  messages: ChatMessage[],
  next: ChatMessage,
): ChatMessage[] {
  return [...messages, next];
}

/**
 * Stream a chat message via SSE.
 * Calls `onEvent` for each parsed SSE event from the server.
 * Returns an AbortController so the caller can cancel.
 */
export function streamChat(
  message: string,
  sessionId: string | undefined,
  onEvent: (event: StreamEvent) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    const STREAM_OPEN_TIMEOUT_MS = 20_000;
    const STREAM_IDLE_TIMEOUT_MS = 45_000;

    const toReadableError = (err: unknown): string => {
      const raw =
        typeof err === "string"
          ? err
          : err instanceof Error
            ? err.message || String(err)
            : String(err ?? "");
      if (
        /load failed|failed to fetch|networkerror|network request failed/i.test(
          raw,
        )
      ) {
        return "网络连接失败：请确认后端服务可用并检查浏览器网络/代理设置。";
      }
      return raw || "Unknown error";
    };

    const fallbackToNonStream = async (reason?: string): Promise<void> => {
      if (controller.signal.aborted) return;
      try {
        const res = await fetch("/api/agent/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId }),
          signal: controller.signal,
          cache: "no-store",
        });

        if (!res.ok) {
          const prefix = reason ? `${reason}; ` : "";
          onEvent({
            type: "error",
            content: `${prefix}HTTP ${res.status}`,
            session_id: sessionId,
          });
          return;
        }

        const data = await res.json();
        const finalContent = String(data?.response ?? "");
        const sid =
          typeof data?.session_id === "string" ? data.session_id : sessionId;
        onEvent({
          type: "done",
          content: finalContent,
          session_id: sid,
        });
      } catch (err) {
        if ((err as any)?.name === "AbortError") return;
        onEvent({
          type: "error",
          content: toReadableError(err),
          session_id: sessionId,
        });
      }
    };

    let timer: ReturnType<typeof setTimeout> | null = null;
    let sawAnyStreamEvent = false;
    let sawTerminalEvent = false;

    const clearTimer = () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    };

    const armTimer = (ms: number, reason: string) => {
      clearTimer();
      timer = setTimeout(() => {
        if (controller.signal.aborted || sawTerminalEvent) return;
        onEvent({
          type: "error",
          content: reason,
          session_id: sessionId,
        });
        controller.abort();
      }, ms);
    };

    try {
      // If stream can't be established in time, fail fast.
      armTimer(
        STREAM_OPEN_TIMEOUT_MS,
        "流式连接超时：后端响应过慢或网络不稳定。",
      );

      const res = await fetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId, stream: true }),
        signal: controller.signal,
        cache: "no-store",
      });

      if (!res.ok || !res.body) {
        clearTimer();
        await fallbackToNonStream(`stream unavailable (HTTP ${res.status})`);
        return;
      }

      // Stream established; now monitor inactivity.
      armTimer(
        STREAM_IDLE_TIMEOUT_MS,
        "流式连接中断：长时间未收到数据，请重试。",
      );

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        armTimer(
          STREAM_IDLE_TIMEOUT_MS,
          "流式连接中断：长时间未收到数据，请重试。",
        );

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const jsonStr = trimmed.slice(6);
          if (!jsonStr || jsonStr === "[DONE]") continue;

          try {
            const event: StreamEvent = JSON.parse(jsonStr);
            sawAnyStreamEvent = true;
            if (event.type === "done" || event.type === "error") {
              sawTerminalEvent = true;
              clearTimer();
            }
            onEvent(event);
          } catch {
            // skip malformed JSON
          }
        }
      }

      // Some proxies close stream without terminal events; don't leave UI hanging.
      if (!sawTerminalEvent) {
        onEvent({
          type: "error",
          content: sawAnyStreamEvent
            ? "流式连接已结束，但未收到完成信号。"
            : "流式连接未返回有效数据。",
          session_id: sessionId,
        });
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        if (!sawAnyStreamEvent) {
          await fallbackToNonStream(toReadableError(err));
        } else {
          onEvent({
            type: "error",
            content: toReadableError(err),
            session_id: sessionId,
          });
        }
      }
    } finally {
      clearTimer();
    }
  })();

  return controller;
}
