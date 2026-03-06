import { useEffect, useMemo, useState } from "react";
import {
  FolderOpen,
  RefreshCw,
  FileText,
  Save,
  RotateCcw,
  MessageCircle,
  Puzzle,
  Timer,
  Heart,
  Settings,
} from "lucide-react";
import {
  getWorkspaceInfo,
  getWorkspaceRelations,
  getWorkspaceFileContent,
  listWorkspaceFiles,
  saveWorkspaceFileContent,
} from "../api";
import type { WorkspaceFileItem } from "../types";
import { PageHeader, EmptyState, Badge } from "../components/ui";
import { IconBadge } from "../components/icons";

function fmtBytes(bytes?: number): string {
  const n = Number(bytes || 0);
  if (!Number.isFinite(n) || n <= 0) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export default function WorkspacePage() {
  const [workspace, setWorkspace] = useState<any>(null);
  const [relations, setRelations] = useState<any>(null);
  const [files, setFiles] = useState<WorkspaceFileItem[]>([]);
  const [selectedPath, setSelectedPath] = useState<string>("");
  const [content, setContent] = useState<string>("");
  const [originalContent, setOriginalContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const hasChanges = content !== originalContent;

  const grouped = useMemo(() => {
    const out = new Map<string, WorkspaceFileItem[]>();
    for (const item of files) {
      const group = item.category || "other";
      if (!out.has(group)) out.set(group, []);
      out.get(group)!.push(item);
    }
    for (const list of out.values()) {
      list.sort((a, b) => a.path.localeCompare(b.path));
    }
    return out;
  }, [files]);

  async function selectFile(path: string) {
    setSelectedPath(path);
    setLoading(true);
    try {
      const data = await getWorkspaceFileContent(path);
      setContent(data.content || "");
      setOriginalContent(data.content || "");
    } finally {
      setLoading(false);
    }
  }

  async function onLoad() {
    setLoading(true);
    try {
      const [ws, rel, fileList] = await Promise.all([
        getWorkspaceInfo(),
        getWorkspaceRelations(),
        listWorkspaceFiles(),
      ]);
      setWorkspace(ws);
      setRelations(rel);
      setFiles(fileList);
      setLoaded(true);

      const existsSelected = fileList.some((f) => f.path === selectedPath);
      if (!selectedPath || !existsSelected) {
        const preferred =
          fileList.find((f) => f.path === "config.json")
          || fileList.find((f) => f.path === "AGENTS.md")
          || fileList.find((f) => f.path === "SOUL.md")
          || fileList[0];
        if (preferred) {
          await selectFile(preferred.path);
        }
      }
    } finally {
      setLoading(false);
    }
  }

  async function onSave() {
    if (!selectedPath) return;
    setSaving(true);
    try {
      await saveWorkspaceFileContent(selectedPath, content);
      setOriginalContent(content);
      await onLoad();
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    void onLoad();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="panel">
      <PageHeader
        title="工作区文件"
        description="查看并编辑关键工作区文件：配置、心跳、定时、会话、技能与记忆文件"
        actions={
          <button onClick={onLoad}>
            <RefreshCw size={15} />
            刷新工作区
          </button>
        }
      />

      {!loaded && (
        <EmptyState
          icon={
            <IconBadge tone="slate">
              <FolderOpen size={20} />
            </IconBadge>
          }
          title="加载工作区信息"
          description="展示关键文件并支持在线修改"
          action={
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              加载
            </button>
          }
        />
      )}

      {relations && (
        <div className="card mb-4">
          <h3>对话 / 技能 / 定时 / 心跳 关系</h3>
          <div className="workspace-rel-grid mt-3">
            <div className="workspace-rel-card">
              <div className="workspace-rel-title">对话</div>
              <div className="workspace-rel-value">
                <IconBadge tone="blue" size="sm">
                  <MessageCircle size={12} />
                </IconBadge>
                sessions: {relations?.chat?.session_total ?? 0}
              </div>
              <div className="workspace-rel-meta">
                chats.json: {relations?.chat?.chats_file_total ?? 0}
              </div>
            </div>
            <div className="workspace-rel-card">
              <div className="workspace-rel-title">技能</div>
              <div className="workspace-rel-value">
                <IconBadge tone="violet" size="sm">
                  <Puzzle size={12} />
                </IconBadge>
                active: {relations?.skills?.active_count ?? 0}
              </div>
              <div className="workspace-rel-meta">
                {(relations?.skills?.active_skills || []).join(", ") || "-"}
              </div>
            </div>
            <div className="workspace-rel-card">
              <div className="workspace-rel-title">定时任务</div>
              <div className="workspace-rel-value">
                <IconBadge tone="amber" size="sm">
                  <Timer size={12} />
                </IconBadge>
                {relations?.cron?.enabled ?? 0}/{relations?.cron?.total ?? 0}
              </div>
              <div className="workspace-rel-meta">enabled / total</div>
            </div>
            <div className="workspace-rel-card">
              <div className="workspace-rel-title">心跳</div>
              <div className="workspace-rel-value">
                <IconBadge tone="danger" size="sm">
                  <Heart size={12} />
                </IconBadge>
                {relations?.heartbeat?.enabled ? "enabled" : "disabled"}
              </div>
              <div className="workspace-rel-meta">
                every: {relations?.heartbeat?.every || "-"} · target:{" "}
                {relations?.heartbeat?.target || "-"}
              </div>
            </div>
            <div className="workspace-rel-card">
              <div className="workspace-rel-title">配置</div>
              <div className="workspace-rel-value">
                <IconBadge tone="teal" size="sm">
                  <Settings size={12} />
                </IconBadge>
                lang: {relations?.config?.language || "-"}
              </div>
              <div className="workspace-rel-meta">
                channels:{" "}
                {(relations?.config?.available_channels || []).join(", ") || "-"}
              </div>
              <div className="workspace-rel-meta">
                last_dispatch: {relations?.config?.last_dispatch || "-"}
              </div>
            </div>
          </div>
          {Array.isArray(relations.links) && relations.links.length > 0 && (
            <div className="mt-3">
              {relations.links.map((line: string) => (
                <div key={line} className="muted text-sm">
                  - {line}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="workspace-layout">
        <div className="workspace-file-list card">
          <h3>关键文件</h3>
          {Array.from(grouped.entries()).map(([group, items]) => (
            <div key={group} className="workspace-group">
              <div className="workspace-group-title">{group}</div>
              {items.map((file) => (
                <button
                  key={file.path}
                  className={`workspace-file-item${
                    selectedPath === file.path ? " active" : ""
                  }`}
                  onClick={() => void selectFile(file.path)}
                >
                  <div className="workspace-file-row">
                    <FileText size={13} />
                    <span className="workspace-file-path">{file.path}</span>
                  </div>
                  <div className="workspace-file-meta">
                    {file.required && <Badge variant="warning">必需</Badge>}
                    {!file.exists && <Badge variant="neutral">未创建</Badge>}
                    {file.exists && <span>{fmtBytes(file.size)}</span>}
                  </div>
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="workspace-editor card">
          <div className="workspace-editor-head">
            <div>
              <h3>{selectedPath || "请选择文件"}</h3>
              {workspace?.working_dir && (
                <div className="muted text-xs mt-2">
                  WORKING_DIR: {workspace.working_dir}
                </div>
              )}
            </div>
            <div className="row">
              <button
                className="btn-secondary btn-sm"
                onClick={() => setContent(originalContent)}
                disabled={!selectedPath || !hasChanges || saving}
              >
                <RotateCcw size={14} />
                重置
              </button>
              <button
                className="btn-sm"
                onClick={() => void onSave()}
                disabled={!selectedPath || !hasChanges || saving}
              >
                <Save size={14} />
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          </div>

          {loading ? (
            <div className="loading-overlay">
              <div className="spinner" />
              <span>加载文件中...</span>
            </div>
          ) : (
            <textarea
              className="workspace-editor-textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={
                selectedPath
                  ? "文件内容为空，可直接编辑后保存"
                  : "左侧选择文件后可编辑"
              }
              disabled={!selectedPath}
            />
          )}
        </div>
      </div>
    </div>
  );
}
