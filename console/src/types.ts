export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type PaperItem = {
  title?: string;
  id?: string;
  published?: string;
  authors?: string[];
  summary?: string;
};

export type SessionItem = {
  session_id: string;
  title?: string;
  created_at?: number;
  updated_at?: number;
  message_count?: number;
};

export type CronJobItem = {
  name: string;
  enabled: boolean;
  running: boolean;
  interval_seconds: number;
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
