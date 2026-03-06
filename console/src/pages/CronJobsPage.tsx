import { useEffect, useMemo, useState } from "react";
import {
  Timer,
  RefreshCw,
  Play,
  Pencil,
  Trash2,
  Plus,
  Save,
  X,
} from "lucide-react";
import {
  createCronJob,
  deleteCronJob,
  getChannels,
  getCronJobs,
  replaceCronJob,
  runCronJobNow,
  toggleCronJob,
} from "../api";
import type { ChannelItem, CronJobItem, CronTaskType } from "../types";
import { PageHeader, EmptyState, Badge, Toggle, DetailModal } from "../components/ui";
import { ChannelGlyph, IconBadge } from "../components/icons";
import { useI18n } from "../i18n";

const DEFAULT_TIMEZONE =
  Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

type CronJobForm = {
  name: string;
  cron: string;
  timezone: string;
  enabled: boolean;
  task_type: CronTaskType;
  content: string;
  channel: string;
  target_user_id: string;
  target_session_id: string;
  mode: "stream" | "final";
  max_concurrency: number;
  timeout_seconds: number;
  misfire_grace_seconds: number;
};

function emptyForm(): CronJobForm {
  return {
    name: "",
    cron: "0 21 * * *",
    timezone: DEFAULT_TIMEZONE,
    enabled: true,
    task_type: "agent",
    content: "",
    channel: "console",
    target_user_id: "main",
    target_session_id: "main",
    mode: "final",
    max_concurrency: 1,
    timeout_seconds: 120,
    misfire_grace_seconds: 60,
  };
}

function extractPrompt(request: CronJobItem["request"]): string {
  if (!request) return "";
  const input = request.input;
  if (typeof input === "string") return input;
  if (Array.isArray(input)) {
    for (const item of input) {
      if (!item || typeof item !== "object") continue;
      const anyItem = item as any;
      if (typeof anyItem.text === "string" && anyItem.text.trim()) {
        return anyItem.text;
      }
      if (Array.isArray(anyItem.content)) {
        for (const part of anyItem.content) {
          if (
            part
            && typeof part === "object"
            && (part as any).type === "text"
            && typeof (part as any).text === "string"
            && (part as any).text.trim()
          ) {
            return (part as any).text;
          }
        }
      }
    }
  }
  return "";
}

function toForm(job: CronJobItem): CronJobForm {
  return {
    name: job.name,
    cron: job.cron,
    timezone: job.timezone,
    enabled: job.enabled,
    task_type: job.task_type,
    content: job.task_type === "text" ? (job.text ?? "") : extractPrompt(job.request),
    channel: job.channel || "console",
    target_user_id: job.target_user_id || "main",
    target_session_id: job.target_session_id || "main",
    mode: job.mode,
    max_concurrency: job.runtime.max_concurrency,
    timeout_seconds: job.runtime.timeout_seconds,
    misfire_grace_seconds: job.runtime.misfire_grace_seconds,
  };
}

function toPayload(form: CronJobForm, editing: CronJobItem | null): CronJobItem {
  const channel = form.channel.trim() || "console";
  const targetUser = form.target_user_id.trim() || "main";
  const targetSession = form.target_session_id.trim() || "main";
  const content = form.content.trim();

  const payload: CronJobItem = {
    id: editing?.id || "",
    name: form.name.trim(),
    enabled: form.enabled,
    task_type: form.task_type,
    cron: form.cron.trim(),
    timezone: form.timezone.trim() || "UTC",
    channel,
    target_user_id: targetUser,
    target_session_id: targetSession,
    mode: form.mode,
    text: form.task_type === "text" ? content : null,
    request:
      form.task_type === "agent"
        ? {
            input: [
              {
                role: "user",
                type: "message",
                content: [{ type: "text", text: content }],
              },
            ],
            user_id: targetUser,
            session_id: targetSession,
            channel,
          }
        : null,
    schedule: {
      type: "cron",
      cron: form.cron.trim(),
      timezone: form.timezone.trim() || "UTC",
    },
    dispatch: {
      type: "channel",
      channel,
      target: {
        user_id: targetUser,
        session_id: targetSession,
      },
      mode: form.mode,
      meta: editing?.dispatch.meta ?? {},
    },
    runtime: {
      max_concurrency: Math.max(1, Math.floor(form.max_concurrency)),
      timeout_seconds: Math.max(1, Math.floor(form.timeout_seconds)),
      misfire_grace_seconds: Math.max(0, Math.floor(form.misfire_grace_seconds)),
    },
    meta: editing?.meta ?? {},
  };
  return payload;
}

export default function CronJobsPage() {
  const { t } = useI18n();
  const [jobs, setJobs] = useState<CronJobItem[]>([]);
  const [channels, setChannels] = useState<string[]>(["console"]);
  const [loaded, setLoaded] = useState(false);
  const [runningJobId, setRunningJobId] = useState<string>("");
  const [togglingJobId, setTogglingJobId] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [deletingJobId, setDeletingJobId] = useState<string>("");
  const [editingJob, setEditingJob] = useState<CronJobItem | null>(null);
  const [form, setForm] = useState<CronJobForm | null>(null);

  const channelOptions = useMemo(() => {
    const names = new Set<string>(["console", ...channels]);
    return [...names].filter((name) => name.trim());
  }, [channels]);

  async function onLoad() {
    const [jobList, channelList] = await Promise.all([
      getCronJobs(),
      getChannels().catch(() => [] as ChannelItem[]),
    ]);
    setJobs(jobList);
    setChannels(channelList.map((ch) => ch.name).filter((name) => !!name));
    setLoaded(true);
  }

  useEffect(() => {
    void onLoad();
  }, []);

  async function onToggle(jobId: string, enabled: boolean) {
    setTogglingJobId(jobId);
    try {
      await toggleCronJob(jobId, enabled);
      await onLoad();
    } finally {
      setTogglingJobId("");
    }
  }

  async function onRunNow(jobId: string) {
    setRunningJobId(jobId);
    try {
      await runCronJobNow(jobId);
      await onLoad();
    } finally {
      setRunningJobId("");
    }
  }

  async function onDelete(job: CronJobItem) {
    if (!window.confirm(t("确认删除定时任务「{name}」吗？", { name: job.name }))) return;
    setDeletingJobId(job.id);
    try {
      await deleteCronJob(job.id);
      if (editingJob?.id === job.id) {
        setEditingJob(null);
        setForm(null);
      }
      await onLoad();
    } finally {
      setDeletingJobId("");
    }
  }

  function onCreate() {
    setEditingJob(null);
    setForm(emptyForm());
  }

  function onEdit(job: CronJobItem) {
    setEditingJob(job);
    setForm(toForm(job));
  }

  function closeModal() {
    setEditingJob(null);
    setForm(null);
  }

  function updateFormField<K extends keyof CronJobForm>(
    key: K,
    value: CronJobForm[K],
  ) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function onSave() {
    if (!form) return;
    if (!form.name.trim()) {
      window.alert(t("任务名称不能为空"));
      return;
    }
    if (!form.cron.trim()) {
      window.alert(t("Cron 表达式不能为空"));
      return;
    }
    if (!form.content.trim()) {
      window.alert(
        form.task_type === "text"
          ? t("文本内容不能为空")
          : t("Agent 提示词不能为空"),
      );
      return;
    }

    const payload = toPayload(form, editingJob);
    setSaving(true);
    try {
      if (editingJob) {
        await replaceCronJob(editingJob.id, payload);
      } else {
        await createCronJob(payload);
      }
      closeModal();
      await onLoad();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel">
      <PageHeader
        title="定时任务"
        description="管理周期性执行的自动化任务（支持编辑、删除、立即执行、通道设置）"
        actions={
          <>
            <button className="btn-secondary" onClick={onCreate}>
              <Plus size={15} />
              新建任务
            </button>
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              刷新任务
            </button>
          </>
        }
      />

      {!loaded && jobs.length === 0 && (
        <EmptyState
          icon={
            <IconBadge tone="amber">
              <Timer size={20} />
            </IconBadge>
          }
          title="加载定时任务"
          description="查看和控制所有自动化定时任务"
          action={
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              加载
            </button>
          }
        />
      )}

      {loaded && jobs.length === 0 && (
        <EmptyState
          icon={
            <IconBadge tone="amber">
              <Timer size={20} />
            </IconBadge>
          }
          title="暂无定时任务"
          description="你可以新建一个定时任务，或在聊天里让 Agent 帮你创建"
          action={
            <button onClick={onCreate}>
              <Plus size={15} />
              新建任务
            </button>
          }
        />
      )}

      <div className="card-list animate-list">
        {jobs.map((job) => (
          <div key={job.id || job.name} className="data-row">
            <div className="data-row-info">
              <div className="data-row-title">
                <Timer
                  size={14}
                  style={{ marginRight: 6, verticalAlign: "middle" }}
                />
                {job.name}
              </div>
              <div className="data-row-meta">
                Cron: {job.cron} ({job.timezone})
                <span style={{ margin: "0 6px" }}>·</span>
                类型: {job.task_type}
                <span style={{ margin: "0 6px" }}>·</span>
                通道:{" "}
                <span className="inline-row">
                  <ChannelGlyph channel={job.channel || "console"} />
                  {job.channel || "console"}
                </span>
                <span style={{ margin: "0 6px" }}>·</span>
                目标: {job.target_user_id || "main"}/{job.target_session_id || "main"}
                <span style={{ margin: "0 6px" }}>·</span>
                模式: {job.mode}
                <span style={{ margin: "0 6px" }}>·</span>
                {job.enabled ? (
                  <Badge variant="success">已启用</Badge>
                ) : (
                  <Badge variant="neutral">已暂停</Badge>
                )}
              </div>
            </div>
            <div className="data-row-actions">
              <button
                className="btn-sm"
                onClick={() => onRunNow(job.id)}
                disabled={runningJobId === job.id}
              >
                <Play size={14} />
                {runningJobId === job.id ? "运行中..." : "马上运行"}
              </button>
              <button className="btn-sm btn-secondary" onClick={() => onEdit(job)}>
                <Pencil size={14} />
                编辑
              </button>
              <button
                className="btn-sm danger"
                onClick={() => onDelete(job)}
                disabled={deletingJobId === job.id}
              >
                <Trash2 size={14} />
                {deletingJobId === job.id ? "删除中..." : "删除"}
              </button>
              <Toggle
                checked={job.enabled}
                disabled={togglingJobId === job.id}
                onChange={(checked) => onToggle(job.id, checked)}
              />
            </div>
          </div>
        ))}
      </div>

      {form && (
        <DetailModal title={editingJob ? "编辑定时任务" : "新建定时任务"} onClose={closeModal}>
          <div className="cron-form-grid">
            <label className="cron-form-field cron-form-span-2">
              <span>任务名称</span>
              <input
                value={form.name}
                onChange={(e) => updateFormField("name", e.target.value)}
                placeholder="例如：每日 arXiv 加密流量分类论文总结"
              />
            </label>

            <label className="cron-form-field">
              <span>Cron 表达式</span>
              <input
                value={form.cron}
                onChange={(e) => updateFormField("cron", e.target.value)}
                placeholder="0 21 * * *"
              />
            </label>

            <label className="cron-form-field">
              <span>时区</span>
              <input
                value={form.timezone}
                onChange={(e) => updateFormField("timezone", e.target.value)}
                placeholder="Asia/Shanghai"
              />
            </label>

            <label className="cron-form-field">
              <span>任务类型</span>
              <select
                value={form.task_type}
                onChange={(e) =>
                  updateFormField("task_type", e.target.value as CronTaskType)
                }
              >
                <option value="agent">agent</option>
                <option value="text">text</option>
              </select>
            </label>

            <label className="cron-form-field">
              <span>通道 (默认 console)</span>
              <input
                list="cron-channel-options"
                value={form.channel}
                onChange={(e) => updateFormField("channel", e.target.value)}
                placeholder="console"
              />
            </label>
            <datalist id="cron-channel-options">
              {channelOptions.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>

            <label className="cron-form-field">
              <span>目标 User ID</span>
              <input
                value={form.target_user_id}
                onChange={(e) => updateFormField("target_user_id", e.target.value)}
                placeholder="main"
              />
            </label>

            <label className="cron-form-field">
              <span>目标 Session ID</span>
              <input
                value={form.target_session_id}
                onChange={(e) =>
                  updateFormField("target_session_id", e.target.value)
                }
                placeholder="main"
              />
            </label>

            <label className="cron-form-field">
              <span>发送模式</span>
              <select
                value={form.mode}
                onChange={(e) =>
                  updateFormField("mode", e.target.value as "stream" | "final")
                }
              >
                <option value="final">final</option>
                <option value="stream">stream</option>
              </select>
            </label>

            <label className="cron-form-field">
              <span>启用状态</span>
              <select
                value={form.enabled ? "enabled" : "paused"}
                onChange={(e) =>
                  updateFormField("enabled", e.target.value === "enabled")
                }
              >
                <option value="enabled">启用</option>
                <option value="paused">暂停</option>
              </select>
            </label>

            <label className="cron-form-field">
              <span>并发上限</span>
              <input
                type="number"
                min={1}
                value={form.max_concurrency}
                onChange={(e) =>
                  updateFormField("max_concurrency", Number(e.target.value) || 1)
                }
              />
            </label>

            <label className="cron-form-field">
              <span>超时秒数</span>
              <input
                type="number"
                min={1}
                value={form.timeout_seconds}
                onChange={(e) =>
                  updateFormField("timeout_seconds", Number(e.target.value) || 120)
                }
              />
            </label>

            <label className="cron-form-field">
              <span>错过触发宽限秒数</span>
              <input
                type="number"
                min={0}
                value={form.misfire_grace_seconds}
                onChange={(e) =>
                  updateFormField(
                    "misfire_grace_seconds",
                    Number(e.target.value) || 0,
                  )
                }
              />
            </label>

            <label className="cron-form-field cron-form-span-2">
              <span>{form.task_type === "text" ? "文本内容" : "Agent 提示词"}</span>
              <textarea
                rows={5}
                value={form.content}
                onChange={(e) => updateFormField("content", e.target.value)}
                placeholder={
                  form.task_type === "text"
                    ? "输入要发送的文本内容"
                    : "例如：请搜索今天 arXiv 的加密流量分类论文并总结"
                }
              />
            </label>
          </div>

          <div className="cron-form-actions">
            <button className="btn-secondary" onClick={closeModal} disabled={saving}>
              <X size={14} />
              取消
            </button>
            <button onClick={onSave} disabled={saving}>
              <Save size={14} />
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        </DetailModal>
      )}
    </div>
  );
}
