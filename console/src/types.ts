export type ChatMessage = {
  role: "user" | "assistant" | "tool";
  content: string;
  /** Thinking/reasoning content (from thinking models) */
  thinking?: string;
  /** Skill traces captured during this turn */
  skillTraces?: SkillTraceInfo[];
  /** Tool calls made in this turn */
  toolCalls?: ToolCallInfo[];
};

export type ToolCallInfo = {
  name: string;
  arguments?: string;
  result?: string;
  status?: "running" | "done" | "error";
  skillId?: string;
  skillName?: string;
};

export type SkillTraceInfo = {
  id: string;
  name: string;
  mode?: string;
  matched?: string[];
  availableTools?: string[];
  calledTools?: ToolCallInfo[];
};

/** SSE event from /api/agent/chat/stream */
export type StreamEvent = {
  type:
    | "thinking"
    | "content"
    | "content_replace"
    | "skill_call"
    | "tool_call"
    | "tool_result"
    | "done"
    | "error";
  content?: string;
  name?: string;
  arguments?: string;
  result?: string;
  skill_id?: string;
  skill_name?: string;
  skill_mode?: string;
  matched?: string[];
  available_tools?: string[];
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

export type CronJobState = {
  next_run_at?: string | null;
  last_run_at?: string | null;
  last_status?: "success" | "error" | "running" | "queued" | "skipped" | null;
  last_error?: string | null;
  pending_runs?: number;
  running_count?: number;
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
  id?: string;
  name?: string;
  enabled?: boolean;
  description?: string;
  source?: string;
  scope?: string;
  path?: string;
  location?: string;
  format?: string;
  diagnostics?: string[];
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

export type WorkflowBinding = {
  agent_id?: string;
  channel?: string;
  user_id?: string;
  session_id?: string;
  cron_job_id?: string;
  automation_run_ids?: string[];
  last_dispatch_at?: string | null;
  last_summary?: string;
};

export type ResearchProjectItem = {
  id: string;
  name: string;
  description?: string;
  status?: string;
  tags?: string[];
  workflow_ids?: string[];
  note_ids?: string[];
  experiment_ids?: string[];
  claim_ids?: string[];
  artifact_ids?: string[];
  paper_refs?: string[];
  paper_watches?: unknown[];
  default_binding?: WorkflowBinding;
  updated_at?: string;
};

export type ResearchWorkflowTask = {
  id: string;
  stage: string;
  title: string;
  description?: string;
  status: string;
  summary?: string;
  due_at?: string | null;
};

export type ResearchWorkflowItem = {
  id: string;
  project_id: string;
  title: string;
  goal?: string;
  status: string;
  current_stage: string;
  tasks?: ResearchWorkflowTask[];
  bindings?: WorkflowBinding;
  note_ids?: string[];
  claim_ids?: string[];
  experiment_ids?: string[];
  updated_at?: string;
};

export type ResearchClaimItem = {
  id: string;
  project_id: string;
  workflow_id?: string;
  text: string;
  status: string;
  confidence?: number | null;
  note_ids?: string[];
  evidence_ids?: string[];
  artifact_ids?: string[];
  updated_at?: string;
};

export type ResearchEvidenceItem = {
  id: string;
  project_id: string;
  workflow_id?: string;
  experiment_id?: string;
  note_id?: string;
  artifact_id?: string;
  evidence_type: string;
  summary: string;
  source?: {
    source_type?: string;
    source_id?: string;
    title?: string;
    locator?: string;
    quote?: string;
    url?: string;
  };
};

export type ResearchReminderItem = {
  id: string;
  reminder_type: string;
  project_id: string;
  workflow_id?: string;
  experiment_id?: string;
  title: string;
  summary: string;
  stage?: string;
};

export type ResearchOverview = {
  counts: {
    projects: number;
    workflows: number;
    active_workflows: number;
    notes: number;
    claims: number;
    evidences: number;
    experiments: number;
    artifacts: number;
  };
  active_workflows: ResearchWorkflowItem[];
  projects: ResearchProjectItem[];
};

export type ResearchDashboard = {
  project: ResearchProjectItem;
  counts: Record<string, number>;
  health: {
    workflows: Record<string, number>;
    experiments: Record<string, number>;
    remediation: Record<string, number>;
  };
  active_workflows: ResearchWorkflowItem[];
  recent_notes: Array<{ id: string; title: string; note_type?: string }>;
  recent_experiments: Array<{ id: string; name: string; status: string }>;
  recent_claims: ResearchClaimItem[];
  recent_drafts: Array<{ id: string; title: string; artifact_type: string }>;
  recent_blockers: Array<{
    kind: string;
    workflow_id?: string;
    experiment_id?: string;
    blocked_task_id?: string;
    blocked_task_title?: string;
    title: string;
    summary: string;
    status: string;
    stage?: string;
    open_remediation_tasks?: number;
    ready_for_retry?: boolean;
    actionable_tasks?: Array<{
      task_id: string;
      title: string;
      status: string;
      assignee?: string;
      action_type?: string;
      target?: string;
      suggested_tool?: string;
      can_dispatch?: boolean;
      can_execute?: boolean;
      dispatch_count?: number;
      execution_count?: number;
      last_dispatch_summary?: string;
      last_execution_summary?: string;
    }>;
  }>;
};

export type ResearchWorkflowTaskActionResult = {
  workflow?: ResearchWorkflowItem;
  task?: ResearchWorkflowTask & {
    dispatch_count?: number;
    execution_count?: number;
    last_dispatch_summary?: string;
    last_execution_summary?: string;
  };
  skipped?: boolean;
  executed?: boolean;
  reason?: string;
  task_kind?: string;
  delivery?: {
    ok?: boolean;
    error?: string;
  };
};

export type ResearchWorkflowRemediationContext = {
  contract_failures: Array<{
    experiment_id?: string;
    experiment_name?: string;
    summary?: string;
    missing_metrics?: string[];
    missing_outputs?: string[];
    missing_artifact_types?: string[];
  }>;
  remediation_summary?: string;
  remediation_actions?: Array<Record<string, unknown>>;
  blocked_task_id?: string;
  blocked_task_title?: string;
  remediation_tasks: Array<{
    id: string;
    title: string;
    status: string;
    assignee?: string;
    action_type?: string;
    target?: string;
    suggested_tool?: string;
    due_at?: string | null;
    dispatch_count?: number;
    execution_count?: number;
    last_dispatch_summary?: string;
    last_execution_summary?: string;
    can_dispatch?: boolean;
    can_execute?: boolean;
  }>;
  ready_for_retry?: boolean;
  retry_exhausted_count?: number;
  retry_exhausted_tasks?: Array<Record<string, unknown>>;
};

export type ResearchWorkflowRemediationBatchResult = {
  workflow?: ResearchWorkflowItem;
  project?: ResearchProjectItem;
  remediation_context?: ResearchWorkflowRemediationContext;
  results?: ResearchWorkflowTaskActionResult[];
  dispatched_count?: number;
  executed_count?: number;
  skipped?: boolean;
  reason?: string;
};

export type ResearchProjectBlockerBatchResult = {
  project?: ResearchProjectItem;
  dashboard?: ResearchDashboard;
  workflow_results?: Array<
    | ResearchWorkflowRemediationBatchResult
    | ResearchWorkflowExecutionResult
  >;
  dispatched_count?: number;
  executed_count?: number;
  resumed_count?: number;
  skipped?: boolean;
  reason?: string;
};

export type ResearchClaimGraph = {
  project?: ResearchProjectItem | null;
  workflow?: ResearchWorkflowItem | null;
  claim: ResearchClaimItem;
  evidences: ResearchEvidenceItem[];
  notes: Array<{ id: string; title: string; content?: string }>;
  artifacts: Array<{ id: string; title: string; artifact_type: string; path?: string }>;
  experiments: Array<{ id: string; name: string; status: string; metrics?: Record<string, unknown> }>;
};

export type ResearchWorkflowExecutionResult = {
  workflow: ResearchWorkflowItem;
  project?: ResearchProjectItem;
  note?: {
    id: string;
    title: string;
    note_type?: string;
    content?: string;
  };
  response?: string;
  mutated_by_agent: boolean;
  agent_id: string;
  session_id: string;
  execution_id: string;
  skipped?: boolean;
  reason?: string;
};
