export type ChatMessage = {
  role: "user" | "assistant" | "tool";
  content: string;
  /** Thinking/reasoning content (from thinking models) */
  thinking?: string;
  /** Tool calls made in this turn */
  toolCalls?: ToolCallInfo[];
};

export type ToolCallInfo = {
  name: string;
  arguments?: string;
  result?: string;
  status?: "running" | "done" | "error";
};

/** SSE event from /api/agent/chat/stream */
export type StreamEvent = {
  type:
    | "thinking"
    | "content"
    | "content_replace"
    | "tool_call"
    | "tool_result"
    | "done"
    | "error";
  content?: string;
  name?: string;
  arguments?: string;
  result?: string;
  session_id?: string;
  agent_id?: string;
};

export type PaperItem = {
  title?: string;
  id?: string;
  published?: string;
  authors?: string[];
  summary?: string;
};

export type CronTaskType = "agent" | "text";

export type CronJobRequest = {
  input: unknown;
  session_id?: string | null;
  user_id?: string | null;
  [key: string]: unknown;
};

export type SessionItem = {
  agent_id?: string;
  session_id: string;
  title?: string;
  created_at?: number;
  updated_at?: number;
  message_count?: number;
};

export type CronJobItem = {
  id: string;
  name: string;
  enabled: boolean;
  task_type: CronTaskType;
  cron: string;
  timezone: string;
  channel: string;
  target_user_id: string;
  target_session_id: string;
  mode: "stream" | "final";
  text?: string | null;
  request?: CronJobRequest | null;
  schedule: {
    type: "cron";
    cron: string;
    timezone: string;
  };
  dispatch: {
    type: "channel";
    channel: string;
    target: {
      user_id: string;
      session_id: string;
    };
    mode: "stream" | "final";
    meta: Record<string, unknown>;
  };
  runtime: {
    max_concurrency: number;
    timeout_seconds: number;
    misfire_grace_seconds: number;
  };
  meta: Record<string, unknown>;
};

export type PushMessage = {
  id: string;
  text: string;
};

export type ChannelItem = {
  name: string;
  type: string;
};

export type EnvItem = {
  key: string;
  value: string;
};

export type SkillItem = {
  name?: string;
  enabled?: boolean;
  description?: string;
};

export type McpClientItem = {
  key: string;
  name?: string;
  transport?: string;
  enabled?: boolean;
  description?: string;
  command?: string;
  args?: string[];
  url?: string;
  env?: Record<string, string>;
};

export type AgentRunningConfig = {
  max_iters: number;
  max_input_length: number;
};

export type ProviderItem = {
  name: string;
  provider_type: string;
  model_name?: string;
  model_names?: string[];
  api_key?: string;
  base_url?: string;
  enabled?: boolean;
  extra?: Record<string, unknown>;
};

export type WorkspaceFileItem = {
  path: string;
  category: string;
  required?: boolean;
  exists: boolean;
  editable: boolean;
  size?: number;
  modified_at?: string | null;
};

export type WorkspaceFileContent = {
  exists: boolean;
  path: string;
  abs_path?: string;
  editable: boolean;
  size?: number;
  modified_at?: string;
  content: string;
};
