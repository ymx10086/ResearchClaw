import type {
  AgentRunningConfig,
  ChannelItem,
  CronJobItem,
  CronJobState,
  EnvItem,
  McpClientItem,
  PaperItem,
  ProviderItem,
  PushMessage,
  ResearchClaimGraph,
  ResearchClaimItem,
  ResearchDashboard,
  ResearchOverview,
  ResearchProjectBlockerBatchResult,
  ResearchProjectItem,
  ResearchReminderItem,
  ResearchWorkflowExecutionResult,
  ResearchWorkflowItem,
  ResearchWorkflowRemediationBatchResult,
  ResearchWorkflowRemediationContext,
  ResearchWorkflowTaskActionResult,
  SessionItem,
  SkillItem,
  StreamEvent,
  WorkspaceFileContent,
  WorkspaceFileItem,
} from "./types";

type JsonInit = Omit<RequestInit, "body"> & { body?: unknown };

async function requestJson<T>(
  path: string,
  errorMessage: string,
  init?: JsonInit,
): Promise<T> {
  const { body, headers, ...rest } = init ?? {};
  const res = await fetch(path, {
    ...rest,
    headers:
      body === undefined
        ? headers
        : {
            "Content-Type": "application/json",
            ...(headers ?? {}),
          },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(errorMessage);
  return res.json();
}

async function requestVoid(
  path: string,
  errorMessage: string,
  init?: JsonInit,
): Promise<void> {
  const { body, headers, ...rest } = init ?? {};
  const res = await fetch(path, {
    ...rest,
    headers:
      body === undefined
        ? headers
        : {
            "Content-Type": "application/json",
            ...(headers ?? {}),
          },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(errorMessage);
}

function withQuery(
  path: string,
  params: Record<string, string | number | boolean | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export async function getHealth(): Promise<{ status: string }> {
  return requestJson("/api/health", "Health check failed");
}

export async function sendChat(
  message: string,
  sessionId?: string,
  agentId?: string,
): Promise<{ response: string; session_id: string }> {
  return requestJson("/api/agent/chat", "Chat request failed", {
    method: "POST",
    body: {
      message,
      session_id: sessionId,
      agent_id: agentId,
    },
  });
}

export async function searchArxiv(
  query: string,
  maxResults = 8,
): Promise<PaperItem[]> {
  const data = await requestJson<{ results?: PaperItem[] }>(
    "/api/papers/search",
    "Paper search failed",
    {
      method: "POST",
      body: { query, source: "arxiv", max_results: maxResults },
    },
  );
  if (Array.isArray(data.results)) return data.results;
  return [];
}

export async function getStatus(): Promise<{
  running: boolean;
  agent_name: string;
  tool_count: number;
}> {
  return requestJson("/api/agent/status", "Status request failed");
}

export async function getResearchOverview(): Promise<ResearchOverview> {
  return requestJson(
    "/api/research/overview",
    "Research overview request failed",
  );
}

export async function listResearchProjects(): Promise<ResearchProjectItem[]> {
  return requestJson(
    "/api/research/projects",
    "Research projects request failed",
  );
}

export async function getResearchProjectDashboard(
  projectId: string,
): Promise<ResearchDashboard> {
  return requestJson(
    `/api/research/projects/${encodeURIComponent(projectId)}/dashboard`,
    "Research project dashboard request failed",
  );
}

export async function listResearchWorkflows(
  projectId?: string,
): Promise<ResearchWorkflowItem[]> {
  return requestJson(
    withQuery("/api/research/workflows", { project_id: projectId }),
    "Research workflows request failed",
  );
}

export async function listResearchClaims(
  projectId?: string,
): Promise<ResearchClaimItem[]> {
  return requestJson(
    withQuery("/api/research/claims", { project_id: projectId }),
    "Research claims request failed",
  );
}

export async function getResearchClaimGraph(
  claimId: string,
): Promise<ResearchClaimGraph> {
  return requestJson(
    `/api/research/claims/${encodeURIComponent(claimId)}/graph`,
    "Claim graph request failed",
  );
}

export async function previewResearchReminders(
  projectId?: string,
): Promise<ResearchReminderItem[]> {
  return requestJson(
    withQuery("/api/research/reminders", { project_id: projectId }),
    "Research reminders request failed",
  );
}

export async function executeResearchWorkflow(
  workflowId: string,
  payload?: { agent_id?: string; session_id?: string },
): Promise<ResearchWorkflowExecutionResult> {
  return requestJson(
    `/api/research/workflows/${encodeURIComponent(workflowId)}/execute`,
    "Research workflow execution failed",
    {
      method: "POST",
      body: {
        agent_id: payload?.agent_id ?? "",
        session_id: payload?.session_id ?? "",
      },
    },
  );
}

export async function dispatchResearchWorkflowTask(
  workflowId: string,
  taskId: string,
): Promise<ResearchWorkflowTaskActionResult> {
  return requestJson(
    `/api/research/workflows/${encodeURIComponent(workflowId)}/tasks/${encodeURIComponent(taskId)}/dispatch`,
    "Research workflow task dispatch failed",
    {
      method: "POST",
    },
  );
}

export async function executeResearchWorkflowTask(
  workflowId: string,
  taskId: string,
): Promise<ResearchWorkflowTaskActionResult> {
  return requestJson(
    `/api/research/workflows/${encodeURIComponent(workflowId)}/tasks/${encodeURIComponent(taskId)}/execute`,
    "Research workflow task execution failed",
    {
      method: "POST",
    },
  );
}

export async function getResearchWorkflowRemediation(
  workflowId: string,
): Promise<ResearchWorkflowRemediationContext> {
  return requestJson(
    `/api/research/workflows/${encodeURIComponent(workflowId)}/remediation`,
    "Research workflow remediation request failed",
  );
}

export async function dispatchResearchWorkflowRemediation(
  workflowId: string,
  limit = 3,
): Promise<ResearchWorkflowRemediationBatchResult> {
  return requestJson(
    withQuery(
      `/api/research/workflows/${encodeURIComponent(workflowId)}/remediation/dispatch`,
      { limit },
    ),
    "Research workflow remediation dispatch failed",
    {
      method: "POST",
    },
  );
}

export async function executeResearchWorkflowRemediation(
  workflowId: string,
  limit = 3,
): Promise<ResearchWorkflowRemediationBatchResult> {
  return requestJson(
    withQuery(
      `/api/research/workflows/${encodeURIComponent(workflowId)}/remediation/execute`,
      { limit },
    ),
    "Research workflow remediation execution failed",
    {
      method: "POST",
    },
  );
}

export async function dispatchResearchProjectBlockers(
  projectId: string,
  workflowLimit = 3,
  taskLimit = 2,
): Promise<ResearchProjectBlockerBatchResult> {
  return requestJson(
    withQuery(
      `/api/research/projects/${encodeURIComponent(projectId)}/blockers/dispatch`,
      { workflow_limit: workflowLimit, task_limit: taskLimit },
    ),
    "Research project blocker dispatch failed",
    {
      method: "POST",
    },
  );
}

export async function executeResearchProjectBlockers(
  projectId: string,
  workflowLimit = 3,
  taskLimit = 2,
): Promise<ResearchProjectBlockerBatchResult> {
  return requestJson(
    withQuery(
      `/api/research/projects/${encodeURIComponent(projectId)}/blockers/execute`,
      { workflow_limit: workflowLimit, task_limit: taskLimit },
    ),
    "Research project blocker execution failed",
    {
      method: "POST",
    },
  );
}

export async function resumeResearchProjectBlockers(
  projectId: string,
  workflowLimit = 3,
): Promise<ResearchProjectBlockerBatchResult> {
  return requestJson(
    withQuery(
      `/api/research/projects/${encodeURIComponent(projectId)}/blockers/resume`,
      { workflow_limit: workflowLimit },
    ),
    "Research project blocker resume failed",
    {
      method: "POST",
    },
  );
}

export async function getControlStatus(): Promise<any> {
  return requestJson("/api/control/status", "Control status request failed");
}

export async function getControlUsage(agentId?: string): Promise<any> {
  return requestJson(
    withQuery("/api/control/usage", { agent_id: agentId }),
    "Control usage request failed",
  );
}

export async function getControlLogs(lines = 200): Promise<{
  path: string;
  lines: number;
  content: string;
}> {
  return requestJson(
    withQuery("/api/control/logs", { lines }),
    "Control logs request failed",
  );
}

export async function reloadControlRuntime(): Promise<any> {
  return requestJson("/api/control/reload", "Control reload failed", {
    method: "POST",
  });
}

export async function applyControlConfig(
  patch: Record<string, unknown>,
  replace = false,
): Promise<any> {
  return requestJson("/api/control/config/apply", "Apply config failed", {
    method: "POST",
    body: { patch, replace },
  });
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
      job?.request &&
      typeof job.request === "object" &&
      "input" in (job.request as Record<string, unknown>)
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
  const data = await requestJson<any[]>(
    "/api/crons/cron/jobs",
    "Cron jobs request failed",
  );
  if (!Array.isArray(data)) return [];
  return data.map((job: any) => normalizeCronJob(job));
}

export async function createCronJob(job: CronJobItem): Promise<CronJobItem> {
  const data = await requestJson<any>(
    "/api/crons/cron/jobs",
    "Create cron job failed",
    {
      method: "POST",
      body: toCronJobPayload(job),
    },
  );
  return normalizeCronJob(data);
}

export async function replaceCronJob(
  jobId: string,
  job: CronJobItem,
): Promise<CronJobItem> {
  const data = await requestJson<any>(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}`,
    "Update cron job failed",
    {
      method: "PUT",
      body: toCronJobPayload(job),
    },
  );
  return normalizeCronJob(data);
}

export async function deleteCronJob(jobId: string): Promise<void> {
  await requestVoid(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}`,
    "Delete cron job failed",
    { method: "DELETE" },
  );
}

export async function getChannels(): Promise<ChannelItem[]> {
  return requestJson("/api/control/channels", "Channels request failed");
}

export async function getChannelCatalog(): Promise<any> {
  return requestJson(
    "/api/control/channels/catalog",
    "Channel catalog request failed",
  );
}

export async function listCustomChannels(): Promise<any[]> {
  const data = await requestJson<{ channels?: any[] }>(
    "/api/control/channels/custom",
    "List custom channels failed",
  );
  return Array.isArray(data?.channels) ? data.channels : [];
}

export async function installCustomChannel(payload: {
  key: string;
  path?: string;
  url?: string;
  overwrite?: boolean;
}): Promise<any> {
  return requestJson(
    "/api/control/channels/custom/install",
    "Install custom channel failed",
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function removeCustomChannel(key: string): Promise<any> {
  return requestJson(
    `/api/control/channels/custom/${encodeURIComponent(key)}`,
    "Remove custom channel failed",
    { method: "DELETE" },
  );
}

export async function getChannelAccounts(): Promise<
  Record<string, Record<string, Record<string, unknown>>>
> {
  const data = await requestJson<{
    channel_accounts?: Record<string, Record<string, Record<string, unknown>>>;
  }>("/api/control/channels/accounts", "Get channel accounts failed");
  return data?.channel_accounts || {};
}

export async function updateChannelAccounts(
  channelAccounts: Record<string, Record<string, Record<string, unknown>>>,
): Promise<any> {
  return requestJson(
    "/api/control/channels/accounts",
    "Update channel accounts failed",
    {
      method: "PUT",
      body: { channel_accounts: channelAccounts },
    },
  );
}

export async function getBindings(): Promise<any[]> {
  const data = await requestJson<{ bindings?: any[] }>(
    "/api/control/bindings",
    "Get bindings failed",
  );
  return Array.isArray(data?.bindings) ? data.bindings : [];
}

export async function updateBindings(bindings: any[]): Promise<any> {
  return requestJson("/api/control/bindings", "Update bindings failed", {
    method: "PUT",
    body: { bindings },
  });
}

export async function getSessions(): Promise<SessionItem[]> {
  return requestJson("/api/control/sessions", "Sessions request failed");
}

export async function getSessionsByAgent(
  agentId?: string,
): Promise<SessionItem[]> {
  return requestJson(
    withQuery("/api/control/sessions", { agent_id: agentId }),
    "Sessions request failed",
  );
}

export async function getSessionDetail(
  sessionId: string,
  agentId?: string,
): Promise<any> {
  return requestJson(
    withQuery(`/api/control/sessions/${encodeURIComponent(sessionId)}`, {
      agent_id: agentId,
    }),
    "Session detail request failed",
  );
}

export async function deleteSession(
  sessionId: string,
  agentId?: string,
): Promise<void> {
  await requestVoid(
    withQuery(`/api/control/sessions/${encodeURIComponent(sessionId)}`, {
      agent_id: agentId,
    }),
    "Delete session failed",
    { method: "DELETE" },
  );
}

export async function getAgents(): Promise<any[]> {
  return requestJson("/api/control/agents", "Agents request failed");
}

export async function toggleCronJob(
  jobId: string,
  enabled: boolean,
): Promise<void> {
  const action = enabled ? "resume" : "pause";
  await requestVoid(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}/${action}`,
    "Toggle cron job failed",
    { method: "POST" },
  );
}

export async function runCronJobNow(jobId: string): Promise<void> {
  await requestVoid(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}/run`,
    "Run cron job failed",
    { method: "POST" },
  );
}

export async function getCronJobState(jobId: string): Promise<CronJobState> {
  return requestJson(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}/state`,
    "Get cron job state failed",
  );
}

export async function stopCronJob(
  jobId: string,
): Promise<{ cancelled: number }> {
  return requestJson(
    `/api/crons/cron/jobs/${encodeURIComponent(jobId)}/stop`,
    "Stop cron job failed",
    { method: "POST" },
  );
}

export async function getConsolePushMessages(
  sessionId?: string,
): Promise<PushMessage[]> {
  const data = await requestJson<{ messages?: any[] }>(
    withQuery("/api/console/push-messages", { session_id: sessionId }),
    "Get console push messages failed",
  );
  if (!Array.isArray(data?.messages)) return [];
  return data.messages
    .map((item: any) => ({
      id: String(item?.id ?? ""),
      text: String(item?.text ?? ""),
    }))
    .filter((item: PushMessage) => item.id && item.text);
}

export async function getHeartbeat(): Promise<any> {
  return requestJson("/api/control/heartbeat", "Heartbeat request failed");
}

export async function listEnvVars(): Promise<EnvItem[]> {
  return requestJson("/api/envs", "List envs failed");
}

export async function saveEnvVars(vars: Record<string, string>): Promise<void> {
  await requestVoid("/api/envs", "Save envs failed", {
    method: "PUT",
    body: vars,
  });
}

export async function listMcpClients(): Promise<McpClientItem[]> {
  return requestJson("/api/mcp", "List MCP clients failed");
}

export async function createMcpClient(
  key: string,
  body: Omit<McpClientItem, "key">,
): Promise<void> {
  await requestVoid(
    withQuery("/api/mcp", { client_key: key }),
    "Create MCP client failed",
    {
      method: "POST",
      body,
    },
  );
}

export async function updateMcpClient(
  key: string,
  body: Omit<McpClientItem, "key">,
): Promise<void> {
  await requestVoid(
    `/api/mcp/${encodeURIComponent(key)}`,
    "Update MCP client failed",
    {
      method: "PUT",
      body,
    },
  );
}

export async function toggleMcpClient(key: string): Promise<void> {
  await requestVoid(
    `/api/mcp/${encodeURIComponent(key)}/toggle`,
    "Toggle MCP client failed",
    { method: "PATCH" },
  );
}

export async function deleteMcpClient(key: string): Promise<void> {
  await requestVoid(
    `/api/mcp/${encodeURIComponent(key)}`,
    "Delete MCP client failed",
    {
      method: "DELETE",
    },
  );
}

export async function getWorkspaceInfo(): Promise<any> {
  return requestJson("/api/workspace", "Workspace info failed");
}

export async function getWorkspaceProfile(): Promise<{
  exists: boolean;
  content: string;
  path?: string;
}> {
  return requestJson("/api/workspace/profile", "Workspace profile failed");
}

export async function listWorkspaceFiles(): Promise<WorkspaceFileItem[]> {
  const data = await requestJson<{ files?: WorkspaceFileItem[] }>(
    "/api/workspace/files",
    "Workspace files request failed",
  );
  return Array.isArray(data?.files) ? data.files : [];
}

export async function getWorkspaceRelations(): Promise<any> {
  return requestJson(
    "/api/workspace/relations",
    "Workspace relations request failed",
  );
}

export async function getWorkspaceFileContent(
  path: string,
): Promise<WorkspaceFileContent> {
  return requestJson(
    withQuery("/api/workspace/file", { path }),
    "Workspace file read failed",
  );
}

export async function saveWorkspaceFileContent(
  path: string,
  content: string,
): Promise<void> {
  await requestVoid("/api/workspace/file", "Workspace file save failed", {
    method: "PUT",
    body: { path, content },
  });
}

export async function listSkills(): Promise<SkillItem[]> {
  const data = await requestJson<{ skills?: SkillItem[] }>(
    "/api/skills",
    "List skills failed",
  );
  return Array.isArray(data.skills) ? data.skills : [];
}

export async function listActiveSkills(): Promise<string[]> {
  const data = await requestJson<{ active_skills?: string[] }>(
    "/api/skills/active",
    "List active skills failed",
  );
  return Array.isArray(data.active_skills) ? data.active_skills : [];
}

export async function enableSkill(skillName: string): Promise<void> {
  await requestVoid("/api/skills/enable", "Enable skill failed", {
    method: "POST",
    body: { skill_name: skillName },
  });
}

export async function disableSkill(skillName: string): Promise<void> {
  await requestVoid("/api/skills/disable", "Disable skill failed", {
    method: "POST",
    body: { skill_name: skillName },
  });
}

export async function getAgentRunningConfig(): Promise<AgentRunningConfig> {
  return requestJson("/api/agent/running-config", "Get agent config failed");
}

export async function updateAgentRunningConfig(
  config: AgentRunningConfig,
): Promise<AgentRunningConfig> {
  return requestJson(
    "/api/agent/running-config",
    "Update agent config failed",
    {
      method: "PUT",
      body: config,
    },
  );
}

export async function listProviders(): Promise<ProviderItem[]> {
  const data = await requestJson<{ providers?: ProviderItem[] }>(
    "/api/providers",
    "List providers failed",
  );
  return Array.isArray(data.providers) ? data.providers : [];
}

export async function createProvider(provider: ProviderItem): Promise<void> {
  await requestVoid("/api/providers", "Create provider failed", {
    method: "POST",
    body: provider,
  });
}

export async function updateProvider(
  name: string,
  settings: Partial<Omit<ProviderItem, "name" | "enabled">>,
): Promise<void> {
  await requestVoid(
    `/api/providers/${encodeURIComponent(name)}/settings`,
    "Update provider failed",
    {
      method: "POST",
      body: settings,
    },
  );
}

export async function setProviderEnabled(
  name: string,
  enabled: boolean,
): Promise<void> {
  const action = enabled ? "enable" : "disable";
  await requestVoid(
    `/api/providers/${encodeURIComponent(name)}/${action}`,
    "Set provider enabled failed",
    { method: "POST" },
  );
}

export async function applyProvider(name: string): Promise<void> {
  await requestVoid(
    `/api/providers/${encodeURIComponent(name)}/apply`,
    "Apply provider failed",
    { method: "POST" },
  );
}

export async function deleteProvider(name: string): Promise<void> {
  await requestVoid(
    `/api/providers/${encodeURIComponent(name)}`,
    "Delete provider failed",
    { method: "DELETE" },
  );
}

export async function listAvailableModels(): Promise<any[]> {
  const data = await requestJson<{ models?: any[] }>(
    "/api/providers/models",
    "List models failed",
  );
  return Array.isArray(data.models) ? data.models : [];
}

/**
 * Stream a chat message via SSE.
 * Calls `onEvent` for each parsed SSE event from the server.
 * Returns an AbortController so the caller can cancel.
 */
export function streamChat(
  message: string,
  sessionId: string | undefined,
  agentId: string | undefined,
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
          body: JSON.stringify({
            message,
            session_id: sessionId,
            agent_id: agentId,
          }),
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
          agent_id: agentId,
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
        body: JSON.stringify({
          message,
          session_id: sessionId,
          agent_id: agentId,
          stream: true,
        }),
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
