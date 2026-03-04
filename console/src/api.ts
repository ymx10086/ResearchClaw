import type {
  AgentRunningConfig,
  ChannelItem,
  ChatMessage,
  CronJobItem,
  EnvItem,
  McpClientItem,
  PaperItem,
  SessionItem,
  SkillItem,
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

export async function getCronJobs(): Promise<CronJobItem[]> {
  const res = await fetch("/api/control/cron-jobs");
  if (!res.ok) throw new Error("Cron jobs request failed");
  return res.json();
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
  name: string,
  enabled: boolean,
): Promise<void> {
  const action = enabled ? "enable" : "disable";
  const res = await fetch(
    `/api/control/cron-jobs/${encodeURIComponent(name)}/${action}`,
    {
      method: "POST",
    },
  );
  if (!res.ok) throw new Error("Toggle cron job failed");
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

export async function listProviders(): Promise<any[]> {
  const res = await fetch("/api/providers");
  if (!res.ok) throw new Error("List providers failed");
  const data = await res.json();
  return Array.isArray(data.providers) ? data.providers : [];
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
