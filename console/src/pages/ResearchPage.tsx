import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bell,
  FileText,
  FolderOpen,
  RefreshCw,
  Workflow,
} from "lucide-react";
import {
  dispatchResearchProjectBlockers,
  dispatchResearchWorkflowRemediation,
  dispatchResearchWorkflowTask,
  executeResearchProjectBlockers,
  executeResearchWorkflow,
  executeResearchWorkflowRemediation,
  executeResearchWorkflowTask,
  getResearchClaimGraph,
  getResearchOverview,
  getResearchProjectDashboard,
  getResearchWorkflowRemediation,
  listResearchClaims,
  listResearchProjects,
  listResearchWorkflows,
  previewResearchReminders,
  resumeResearchProjectBlockers,
} from "../api";
import {
  Badge,
  DataRow,
  DetailModal,
  EmptyState,
  Loading,
  NoticeBanner,
  PageHeader,
  StatCard,
  SurfaceCard,
} from "../components/ui";
import { useI18n } from "../i18n";
import type {
  ResearchClaimGraph,
  ResearchClaimItem,
  ResearchDashboard,
  ResearchOverview,
  ResearchProjectItem,
  ResearchReminderItem,
  ResearchWorkflowRemediationContext,
  ResearchWorkflowItem,
} from "../types";

function statusVariant(
  status: string,
): "success" | "warning" | "danger" | "info" | "neutral" {
  const normalized = String(status || "").toLowerCase();
  if (["completed", "supported", "active"].includes(normalized)) {
    return "success";
  }
  if (["blocked", "failed", "disputed", "cancelled"].includes(normalized)) {
    return "danger";
  }
  if (["paused", "needs_review"].includes(normalized)) {
    return "warning";
  }
  if (["running", "queued", "draft"].includes(normalized)) {
    return "info";
  }
  return "neutral";
}

export default function ResearchPage() {
  const { t } = useI18n();
  const [overview, setOverview] = useState<ResearchOverview | null>(null);
  const [projects, setProjects] = useState<ResearchProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [dashboard, setDashboard] = useState<ResearchDashboard | null>(null);
  const [workflows, setWorkflows] = useState<ResearchWorkflowItem[]>([]);
  const [claims, setClaims] = useState<ResearchClaimItem[]>([]);
  const [reminders, setReminders] = useState<ResearchReminderItem[]>([]);
  const [claimGraph, setClaimGraph] = useState<ResearchClaimGraph | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [claimLoadingId, setClaimLoadingId] = useState("");
  const [executingWorkflowId, setExecutingWorkflowId] = useState("");
  const [taskActionKey, setTaskActionKey] = useState("");
  const [projectActionKey, setProjectActionKey] = useState("");
  const [notice, setNotice] = useState<{
    variant: "success" | "warning" | "danger" | "info";
    text: string;
  } | null>(null);
  const [remediationModal, setRemediationModal] = useState<{
    workflowId: string;
    title: string;
  } | null>(null);
  const [remediationContext, setRemediationContext] =
    useState<ResearchWorkflowRemediationContext | null>(null);
  const [remediationLoading, setRemediationLoading] = useState(false);

  const loadProjectContext = useCallback(async (projectId: string) => {
    const [dashboardData, workflowData, claimData, reminderData] =
      await Promise.all([
        getResearchProjectDashboard(projectId),
        listResearchWorkflows(projectId),
        listResearchClaims(projectId),
        previewResearchReminders(projectId),
      ]);
    setDashboard(dashboardData);
    setWorkflows(workflowData);
    setClaims(claimData);
    setReminders(reminderData);
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [overviewData, projectData] = await Promise.all([
        getResearchOverview(),
        listResearchProjects(),
      ]);
      setOverview(overviewData);
      setProjects(projectData);

      const nextProjectId =
        selectedProjectId || projectData[0]?.id || overviewData.projects[0]?.id;
      if (nextProjectId) {
        setSelectedProjectId(nextProjectId);
        await loadProjectContext(nextProjectId);
      } else {
        setDashboard(null);
        setWorkflows([]);
        setClaims([]);
        setReminders([]);
      }
    } finally {
      setLoading(false);
    }
  }, [loadProjectContext, selectedProjectId]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!selectedProjectId) return;
    void loadProjectContext(selectedProjectId);
  }, [loadProjectContext, selectedProjectId]);

  async function openClaimGraph(claimId: string) {
    setClaimLoadingId(claimId);
    try {
      const graph = await getResearchClaimGraph(claimId);
      setClaimGraph(graph);
    } finally {
      setClaimLoadingId("");
    }
  }

  async function executeWorkflow(workflowId: string) {
    setExecutingWorkflowId(workflowId);
    try {
      await executeResearchWorkflow(workflowId);
      await refreshResearchViews();
    } finally {
      setExecutingWorkflowId("");
    }
  }

  const refreshResearchViews = useCallback(
    async (workflowId?: string) => {
      const [overviewData] = await Promise.all([
        getResearchOverview(),
        selectedProjectId ? loadProjectContext(selectedProjectId) : Promise.resolve(),
      ]);
      setOverview(overviewData);
      if (workflowId) {
        const context = await getResearchWorkflowRemediation(workflowId);
        setRemediationContext(context);
      }
    },
    [loadProjectContext, selectedProjectId],
  );

  async function openRemediationDetails(workflowId: string, title: string) {
    setRemediationModal({ workflowId, title });
    setRemediationLoading(true);
    try {
      const context = await getResearchWorkflowRemediation(workflowId);
      setRemediationContext(context);
    } finally {
      setRemediationLoading(false);
    }
  }

  async function runBlockerTaskAction(
    workflowId: string,
    taskId: string,
    mode: "dispatch" | "execute",
  ) {
    const actionKey = `${mode}:${taskId}`;
    setTaskActionKey(actionKey);
    setNotice(null);
    try {
      const result =
        mode === "dispatch"
          ? await dispatchResearchWorkflowTask(workflowId, taskId)
          : await executeResearchWorkflowTask(workflowId, taskId);
      await refreshResearchViews(
        remediationModal?.workflowId === workflowId ? workflowId : undefined,
      );
      const summary =
        result.reason ||
        result.task?.last_execution_summary ||
        result.task?.last_dispatch_summary ||
        (mode === "dispatch" ? t("任务已派发。") : t("任务已执行。"));
      setNotice({
        variant: result.skipped ? "warning" : "success",
        text: summary,
      });
    } catch (error: any) {
      setNotice({
        variant: "danger",
        text: error?.message || t("任务操作失败"),
      });
    } finally {
      setTaskActionKey("");
    }
  }

  async function runRemediationBatchAction(
    workflowId: string,
    mode: "dispatch" | "execute",
  ) {
    const actionKey = `${mode}-remediation:${workflowId}`;
    setTaskActionKey(actionKey);
    setNotice(null);
    try {
      const result =
        mode === "dispatch"
          ? await dispatchResearchWorkflowRemediation(workflowId, 3)
          : await executeResearchWorkflowRemediation(workflowId, 3);
      await refreshResearchViews(workflowId);
      const summary =
        result.reason ||
        (mode === "dispatch"
          ? t(`已派发 ${result.dispatched_count || 0} 个 remediation task。`)
          : t(`已执行 ${result.executed_count || 0} 个 remediation task。`));
      setNotice({
        variant: result.skipped ? "warning" : "success",
        text: summary,
      });
    } catch (error: any) {
      setNotice({
        variant: "danger",
        text: error?.message || t("批量 remediation 操作失败"),
      });
    } finally {
      setTaskActionKey("");
    }
  }

  async function runProjectBlockerAction(
    projectId: string,
    mode: "dispatch" | "execute" | "resume",
  ) {
    const actionKey = `${mode}:${projectId}`;
    setProjectActionKey(actionKey);
    setNotice(null);
    try {
      const result =
        mode === "dispatch"
          ? await dispatchResearchProjectBlockers(projectId, 3, 2)
          : mode === "execute"
            ? await executeResearchProjectBlockers(projectId, 3, 2)
            : await resumeResearchProjectBlockers(projectId, 3);
      await refreshResearchViews(
        remediationModal?.workflowId && remediationContext
          ? remediationModal.workflowId
          : undefined,
      );
      const summary =
        result.reason ||
        (mode === "dispatch"
          ? t(`已为 project 派发 ${result.dispatched_count || 0} 个 blocker task。`)
          : mode === "execute"
            ? t(`已为 project 执行 ${result.executed_count || 0} 个 blocker task。`)
            : t(`已恢复推进 ${result.resumed_count || 0} 个 workflow。`));
      setNotice({
        variant: result.skipped ? "warning" : "success",
        text: summary,
      });
    } catch (error: any) {
      setNotice({
        variant: "danger",
        text: error?.message || t("Project blocker 操作失败"),
      });
    } finally {
      setProjectActionKey("");
    }
  }

  return (
    <div className="panel">
      <PageHeader
        eyebrow="Research OS"
        title={t("研究项目")}
        description={t(
          "按课题查看 workflow、claim、evidence、notes 和主动提醒。",
        )}
        actions={
          <button className="btn-ghost" onClick={() => void loadAll()}>
            <RefreshCw size={15} />
            {t("刷新")}
          </button>
        }
      />

      {loading && <Loading text={t("加载中...")} />}
      {notice && <NoticeBanner variant={notice.variant}>{notice.text}</NoticeBanner>}

      <div className="card-grid">
        <StatCard
          label={t("研究项目")}
          value={overview?.counts.projects ?? 0}
          icon={<FolderOpen size={18} />}
        />
        <StatCard
          label={t("活跃工作流")}
          value={overview?.counts.active_workflows ?? 0}
          icon={<Workflow size={18} />}
          variant="info"
        />
        <StatCard
          label={t("结构化笔记")}
          value={overview?.counts.notes ?? 0}
          icon={<FileText size={18} />}
          variant="success"
        />
        <StatCard
          label={t("证据项")}
          value={overview?.counts.evidences ?? 0}
          icon={<Activity size={18} />}
          variant="warning"
        />
      </div>

      <div className="card-grid">
        <SurfaceCard
          title={t("项目列表")}
          description={t("选择一个项目，下钻查看 workflow、claim 与提醒。")}
        >
          {projects.length === 0 ? (
            <EmptyState
              icon={<FolderOpen size={28} />}
              title={t("暂无研究项目")}
              description={t("先通过 API 创建 project，再在这里查看闭环进展。")}
            />
          ) : (
            projects.map((project) => (
              <DataRow
                key={project.id}
                title={project.name}
                meta={project.description || project.id}
                badge={
                  <Badge variant={statusVariant(project.status || "active")}>
                    {project.status || "active"}
                  </Badge>
                }
                actions={
                  <button
                    className="btn-ghost btn-sm"
                    onClick={() => setSelectedProjectId(project.id)}
                  >
                    {selectedProjectId === project.id ? t("查看") : t("加载")}
                  </button>
                }
              />
            ))
          )}
        </SurfaceCard>

        <SurfaceCard
          title={t("项目概览")}
          description={
            dashboard
              ? `${dashboard.project.name} · ${dashboard.project.status || "active"}`
              : t("选择项目后显示聚合统计与近期活动。")
          }
        >
          {dashboard ? (
            <div className="page-header-meta-row">
              {Object.entries(dashboard.counts).map(([key, value]) => (
                <div key={key} className="metric-pill">
                  <span>{key}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Activity size={28} />}
              title={t("等待项目上下文")}
              description={t("选中一个 project 后，这里会显示聚合指标。")}
            />
          )}
        </SurfaceCard>
      </div>

      <div className="card-grid">
        <SurfaceCard
          title={t("工作流")}
          description={t("聚焦当前 stage、状态以及是否已经进入阻塞或写作阶段。")}
        >
          {workflows.length === 0 ? (
            <EmptyState
              icon={<Workflow size={28} />}
              title={t("暂无工作流")}
              description={t("当前项目还没有 workflow。")}
            />
          ) : (
            workflows.slice(0, 8).map((workflow) => (
              <DataRow
                key={workflow.id}
                title={workflow.title}
                meta={`${workflow.current_stage} · ${workflow.bindings?.last_summary || workflow.goal || workflow.id}`}
                badge={
                  <Badge variant={statusVariant(workflow.status)}>
                    {workflow.status}
                  </Badge>
                }
                actions={
                  <button
                    className="btn-ghost btn-sm"
                    disabled={executingWorkflowId === workflow.id}
                    onClick={() => void executeWorkflow(workflow.id)}
                  >
                    {executingWorkflowId === workflow.id ? t("执行中...") : t("推进")}
                  </button>
                }
              />
            ))
          )}
        </SurfaceCard>

        <SurfaceCard
          title={t("执行健康度")}
          description={t("汇总 project 下 experiment contract、bundle 校验和 remediation 压力。")}
        >
          {dashboard ? (
            <div className="form-stack">
              {Object.entries(dashboard.health).map(([section, values]) => (
                <div key={section}>
                  <h4>{section}</h4>
                  <div className="page-header-meta-row">
                    {Object.entries(values).map(([key, value]) => (
                      <div key={`${section}-${key}`} className="metric-pill">
                        <span>{key}</span>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Activity size={28} />}
              title={t("等待健康度统计")}
              description={t("选中一个 project 后，这里会显示 execution health。")}
            />
          )}
        </SurfaceCard>
      </div>

      <div className="card-grid">
        <SurfaceCard
          title={t("近期阻塞")}
          description={t("优先显示 blocked workflow、未收口 remediation 和可重试实验。")}
          actions={
            selectedProjectId && dashboard?.recent_blockers.length ? (
              <>
                <button
                  className="btn-ghost btn-sm"
                  disabled={projectActionKey === `dispatch:${selectedProjectId}`}
                  onClick={() =>
                    void runProjectBlockerAction(selectedProjectId, "dispatch")
                  }
                >
                  {projectActionKey === `dispatch:${selectedProjectId}`
                    ? t("项目派发中...")
                    : t("项目批量派发")}
                </button>
                <button
                  className="btn-ghost btn-sm"
                  disabled={projectActionKey === `execute:${selectedProjectId}`}
                  onClick={() =>
                    void runProjectBlockerAction(selectedProjectId, "execute")
                  }
                >
                  {projectActionKey === `execute:${selectedProjectId}`
                    ? t("项目执行中...")
                    : t("项目批量执行")}
                </button>
                <button
                  className="btn-ghost btn-sm"
                  disabled={projectActionKey === `resume:${selectedProjectId}`}
                  onClick={() =>
                    void runProjectBlockerAction(selectedProjectId, "resume")
                  }
                >
                  {projectActionKey === `resume:${selectedProjectId}`
                    ? t("恢复中...")
                    : t("恢复可重试")}
                </button>
              </>
            ) : undefined
          }
        >
          {!dashboard || dashboard.recent_blockers.length === 0 ? (
            <EmptyState
              icon={<AlertTriangle size={28} />}
              title={t("暂无显著阻塞")}
              description={t("当前 project 没有需要优先处理的 contract 或 workflow blocker。")}
            />
          ) : (
            dashboard.recent_blockers.map((blocker) => {
              const primaryTask = blocker.actionable_tasks?.[0];
              return (
                <DataRow
                  key={`${blocker.kind}-${blocker.workflow_id || blocker.experiment_id || blocker.title}`}
                  title={blocker.title}
                  meta={`${blocker.stage || blocker.kind} · ${blocker.summary}${primaryTask?.title ? ` · ${primaryTask.title}` : ""}`}
                  badge={
                    <Badge variant={statusVariant(blocker.status || "blocked")}>
                      {blocker.ready_for_retry ? t("ready_for_retry") : blocker.status}
                    </Badge>
                  }
                  actions={
                    blocker.workflow_id ? (
                      <>
                        <button
                          className="btn-ghost btn-sm"
                          onClick={() =>
                            void openRemediationDetails(
                              blocker.workflow_id || "",
                              blocker.title,
                            )
                          }
                        >
                          {t("详情")}
                        </button>
                        {primaryTask && (
                          <>
                            <button
                              className="btn-ghost btn-sm"
                              disabled={
                                !primaryTask.can_dispatch ||
                                taskActionKey === `dispatch:${primaryTask.task_id}`
                              }
                              onClick={() =>
                                void runBlockerTaskAction(
                                  blocker.workflow_id || "",
                                  primaryTask.task_id,
                                  "dispatch",
                                )
                              }
                            >
                              {taskActionKey === `dispatch:${primaryTask.task_id}`
                                ? t("派发中...")
                                : t("派发")}
                            </button>
                            <button
                              className="btn-ghost btn-sm"
                              disabled={
                                !primaryTask.can_execute ||
                                taskActionKey === `execute:${primaryTask.task_id}`
                              }
                              onClick={() =>
                                void runBlockerTaskAction(
                                  blocker.workflow_id || "",
                                  primaryTask.task_id,
                                  "execute",
                                )
                              }
                            >
                              {taskActionKey === `execute:${primaryTask.task_id}`
                                ? t("执行中...")
                                : t("执行")}
                            </button>
                          </>
                        )}
                      </>
                    ) : undefined
                  }
                />
              );
            })
          )}
        </SurfaceCard>

        <SurfaceCard
          title={t("主动提醒")}
          description={t("这里展示当前到期的 follow-up、写作待办和实验回看提醒。")}
        >
          {reminders.length === 0 ? (
            <EmptyState
              icon={<Bell size={28} />}
              title={t("暂无到期提醒")}
              description={t("当前没有需要主动推进的研究提醒。")}
            />
          ) : (
            reminders.map((reminder) => (
              <DataRow
                key={reminder.id}
                title={reminder.title}
                meta={reminder.summary}
                badge={<Badge variant="warning">{reminder.reminder_type}</Badge>}
              />
            ))
          )}
        </SurfaceCard>
      </div>

      <SurfaceCard
        title={t("Claim 与证据链")}
        description={t("打开某个 claim，查看它当前连接的 evidence、notes、artifacts 与 experiments。")}
      >
        {claims.length === 0 ? (
          <EmptyState
            icon={<Activity size={28} />}
            title={t("暂无 claim")}
            description={t("当前项目还没有结构化 claim。")}
          />
        ) : (
          claims.slice(0, 10).map((claim) => (
            <DataRow
              key={claim.id}
              title={claim.text}
              meta={`evidence=${claim.evidence_ids?.length || 0} · notes=${claim.note_ids?.length || 0}`}
              badge={
                <Badge variant={statusVariant(claim.status)}>{claim.status}</Badge>
              }
              actions={
                <button
                  className="btn-ghost btn-sm"
                  disabled={claimLoadingId === claim.id}
                  onClick={() => void openClaimGraph(claim.id)}
                >
                  {claimLoadingId === claim.id ? t("加载中...") : t("查看")}
                </button>
              }
            />
          ))
        )}
      </SurfaceCard>

      {claimGraph && (
        <DetailModal
          title={t("Claim 证据详情")}
          onClose={() => setClaimGraph(null)}
        >
          <div className="form-stack">
            <div>
              <h4>{claimGraph.claim.text}</h4>
              <p className="muted text-sm">
                {claimGraph.project?.name || "-"} · {claimGraph.claim.status}
              </p>
            </div>
            <div>
              <h4>{t("Evidence")}</h4>
              {claimGraph.evidences.length === 0 ? (
                <p className="muted text-sm">{t("暂无证据")}</p>
              ) : (
                claimGraph.evidences.map((item) => (
                  <div key={item.id} className="pre">
                    <strong>{item.evidence_type}</strong>
                    <p>{item.summary}</p>
                    {item.source?.title && (
                      <p className="muted text-sm">
                        {item.source.title}
                        {item.source.locator ? ` · ${item.source.locator}` : ""}
                      </p>
                    )}
                    {item.source?.quote && (
                      <pre>{item.source.quote}</pre>
                    )}
                  </div>
                ))
              )}
            </div>
            <div>
              <h4>{t("关联对象")}</h4>
              <p className="muted text-sm">
                notes={claimGraph.notes.length} · artifacts={claimGraph.artifacts.length} · experiments=
                {claimGraph.experiments.length}
              </p>
            </div>
          </div>
        </DetailModal>
      )}

      {remediationModal && (
        <DetailModal
          title={`${t("Remediation 详情")} · ${remediationModal.title}`}
          onClose={() => {
            setRemediationModal(null);
            setRemediationContext(null);
          }}
        >
          {remediationLoading ? (
            <Loading text={t("加载 remediation 上下文...")} />
          ) : remediationContext ? (
            <div className="form-stack">
              <div className="page-header-meta-row">
                <div className="metric-pill">
                  <span>{t("ready_for_retry")}</span>
                  <strong>{String(Boolean(remediationContext.ready_for_retry))}</strong>
                </div>
                <div className="metric-pill">
                  <span>{t("retry_exhausted")}</span>
                  <strong>{remediationContext.retry_exhausted_count || 0}</strong>
                </div>
                <div className="metric-pill">
                  <span>{t("open_tasks")}</span>
                  <strong>{remediationContext.remediation_tasks.length}</strong>
                </div>
              </div>
              <p className="muted text-sm">
                {remediationContext.remediation_summary || t("暂无 remediation 摘要")}
              </p>
              <div className="page-header-actions">
                <button
                  className="btn-ghost btn-sm"
                  disabled={
                    !remediationContext.ready_for_retry ||
                    executingWorkflowId === remediationModal.workflowId
                  }
                  onClick={() => void executeWorkflow(remediationModal.workflowId)}
                >
                  {executingWorkflowId === remediationModal.workflowId
                    ? t("恢复中...")
                    : t("继续推进")}
                </button>
                <button
                  className="btn-ghost btn-sm"
                  disabled={
                    taskActionKey ===
                    `dispatch-remediation:${remediationModal.workflowId}`
                  }
                  onClick={() =>
                    void runRemediationBatchAction(
                      remediationModal.workflowId,
                      "dispatch",
                    )
                  }
                >
                  {taskActionKey ===
                  `dispatch-remediation:${remediationModal.workflowId}`
                    ? t("批量派发中...")
                    : t("批量派发")}
                </button>
                <button
                  className="btn-ghost btn-sm"
                  disabled={
                    taskActionKey ===
                    `execute-remediation:${remediationModal.workflowId}`
                  }
                  onClick={() =>
                    void runRemediationBatchAction(
                      remediationModal.workflowId,
                      "execute",
                    )
                  }
                >
                  {taskActionKey ===
                  `execute-remediation:${remediationModal.workflowId}`
                    ? t("批量执行中...")
                    : t("批量执行")}
                </button>
              </div>
              <div>
                <h4>{t("Contract Failures")}</h4>
                {remediationContext.contract_failures.length === 0 ? (
                  <p className="muted text-sm">{t("暂无 contract failure")}</p>
                ) : (
                  remediationContext.contract_failures.map((failure) => (
                    <div
                      key={`${failure.experiment_id || failure.experiment_name}`}
                      className="pre"
                    >
                      <strong>{failure.experiment_name || failure.experiment_id}</strong>
                      <p>{failure.summary}</p>
                    </div>
                  ))
                )}
              </div>
              <div>
                <h4>{t("Remediation Tasks")}</h4>
                {remediationContext.remediation_tasks.length === 0 ? (
                  <p className="muted text-sm">{t("暂无 remediation task")}</p>
                ) : (
                  remediationContext.remediation_tasks.map((task) => (
                    <DataRow
                      key={task.id}
                      title={task.title}
                      meta={`${task.action_type || "generic"} · ${task.target || task.suggested_tool || task.assignee || "-"}`}
                      badge={
                        <Badge variant={statusVariant(task.status || "pending")}>
                          {task.status}
                        </Badge>
                      }
                      actions={
                        <>
                          <button
                            className="btn-ghost btn-sm"
                            disabled={
                              !task.can_dispatch ||
                              taskActionKey === `dispatch:${task.id}`
                            }
                            onClick={() =>
                              void runBlockerTaskAction(
                                remediationModal.workflowId,
                                task.id,
                                "dispatch",
                              )
                            }
                          >
                            {taskActionKey === `dispatch:${task.id}`
                              ? t("派发中...")
                              : t("派发")}
                          </button>
                          <button
                            className="btn-ghost btn-sm"
                            disabled={
                              !task.can_execute ||
                              taskActionKey === `execute:${task.id}`
                            }
                            onClick={() =>
                              void runBlockerTaskAction(
                                remediationModal.workflowId,
                                task.id,
                                "execute",
                              )
                            }
                          >
                            {taskActionKey === `execute:${task.id}`
                              ? t("执行中...")
                              : t("执行")}
                          </button>
                        </>
                      }
                    />
                  ))
                )}
              </div>
            </div>
          ) : (
            <EmptyState
              icon={<AlertTriangle size={28} />}
              title={t("暂无 remediation 详情")}
              description={t("当前 workflow 没有可用的 remediation context。")}
            />
          )}
        </DetailModal>
      )}
    </div>
  );
}
