import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import {
  Server,
  RefreshCw,
  Plus,
  Trash2,
  Edit2,
  Save,
  X,
  Globe,
  Key,
  Play,
  CheckCircle,
} from "lucide-react";
import {
  listProviders,
  createProvider,
  updateProvider,
  setProviderEnabled,
  applyProvider,
  deleteProvider,
} from "../api";
import type { ProviderItem } from "../types";
import { PageHeader, EmptyState, Badge, Toggle } from "../components/ui";
import { useI18n } from "../i18n";

const PROVIDER_TYPES = [
  "openai",
  "anthropic",
  "ollama",
  "dashscope",
  "deepseek",
  "other",
];

const EMPTY_FORM: ProviderItem = {
  name: "",
  provider_type: "openai",
  model_name: "",
  api_key: "",
  base_url: "",
};

type EditForm = Pick<
  ProviderItem,
  "provider_type" | "model_name" | "api_key" | "base_url"
>;

export default function ModelsPage() {
  const { t } = useI18n();
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [loaded, setLoaded] = useState(false);

  // State for add-new form
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState<ProviderItem>({ ...EMPTY_FORM });
  const [addSaving, setAddSaving] = useState(false);

  // State for inline edit
  const [editingName, setEditingName] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({
    provider_type: "openai",
    model_name: "",
    api_key: "",
    base_url: "",
  });
  const [editSaving, setEditSaving] = useState(false);

  // Applying state
  const [applyingName, setApplyingName] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  function showSuccess(msg: string) {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3000);
  }

  async function onLoad() {
    setError(null);
    try {
      setProviders(await listProviders());
      setLoaded(true);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    }
  }

  useEffect(() => {
    void onLoad();
  }, []);

  // ── Add new provider ────────────────────────────────────────────────────

  function startAdd() {
    setAddForm({ ...EMPTY_FORM });
    setShowAdd(true);
    setEditingName(null);
  }

  function cancelAdd() {
    setShowAdd(false);
    setAddForm({ ...EMPTY_FORM });
  }

  async function onAdd() {
    if (!addForm.name.trim() || !addForm.provider_type.trim()) {
      setError("名称和供应商类型不能为空");
      return;
    }
    setAddSaving(true);
    setError(null);
    try {
      await createProvider(addForm);
      cancelAdd();
      await onLoad();
      showSuccess(`供应商 "${addForm.name}" 已添加`);
    } catch (e: any) {
      setError(e?.message || "添加失败");
    } finally {
      setAddSaving(false);
    }
  }

  // ── Inline edit settings ────────────────────────────────────────────────

  function startEdit(p: ProviderItem) {
    setEditingName(p.name);
    setEditForm({
      provider_type: p.provider_type,
      model_name: p.model_name ?? "",
      api_key: "", // never pre-fill masked key
      base_url: p.base_url ?? "",
    });
    setShowAdd(false);
  }

  function cancelEdit() {
    setEditingName(null);
  }

  async function onSaveEdit(name: string) {
    setEditSaving(true);
    setError(null);
    try {
      const payload: Partial<EditForm> = {
        provider_type: editForm.provider_type,
        model_name: editForm.model_name,
        base_url: editForm.base_url,
      };
      // Only include api_key if user typed something
      if (editForm.api_key) payload.api_key = editForm.api_key;
      await updateProvider(name, payload);
      setEditingName(null);
      await onLoad();
      showSuccess(`供应商 "${name}" 设置已保存`);
    } catch (e: any) {
      setError(e?.message || "保存失败");
    } finally {
      setEditSaving(false);
    }
  }

  // ── Enable / disable ────────────────────────────────────────────────────

  async function onToggleEnabled(p: ProviderItem) {
    setError(null);
    try {
      await setProviderEnabled(p.name, !p.enabled);
      await onLoad();
    } catch (e: any) {
      setError(e?.message || "切换失败");
    }
  }

  // ── Apply to agent ──────────────────────────────────────────────────────

  async function onApply(name: string) {
    setApplyingName(name);
    setError(null);
    try {
      await applyProvider(name);
      await onLoad();
      showSuccess(`已将 "${name}" 应用到 Agent，配置生效`);
    } catch (e: any) {
      setError(e?.message || "应用失败");
    } finally {
      setApplyingName(null);
    }
  }

  // ── Delete ──────────────────────────────────────────────────────────────

  async function onDelete(name: string) {
    if (!window.confirm(t('确定删除供应商 "{name}"？', { name }))) return;
    setError(null);
    try {
      await deleteProvider(name);
      await onLoad();
    } catch (e: any) {
      setError(e?.message || "删除失败");
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────────

  function setAddField(key: keyof ProviderItem, value: string) {
    setAddForm((prev) => ({ ...prev, [key]: value }));
  }

  function setEditField(key: keyof EditForm, value: string) {
    setEditForm((prev) => ({ ...prev, [key]: value }));
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="panel">
      <PageHeader
        title="模型 & 供应商"
        description="管理 LLM 供应商配置；启用一个供应商，点击「应用到 Agent」即可热更新"
        actions={
          <div className="row">
            <button className="btn-secondary" onClick={startAdd}>
              <Plus size={15} />
              新增供应商
            </button>
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              刷新
            </button>
          </div>
        }
      />

      {/* Toast messages */}
      {error && (
        <div
          className="badge badge-danger"
          style={{ display: "block", marginBottom: 12, padding: "8px 12px" }}
        >
          {error}
        </div>
      )}
      {successMsg && (
        <div
          className="badge badge-success"
          style={{ display: "block", marginBottom: 12, padding: "8px 12px" }}
        >
          <CheckCircle
            size={13}
            style={{ marginRight: 6, verticalAlign: "middle" }}
          />
          {successMsg}
        </div>
      )}

      {/* Add new provider form */}
      {showAdd && (
        <div
          className="card mb-4"
          style={{ border: "1.5px solid var(--color-brand)", padding: 20 }}
        >
          <h4 style={{ marginBottom: 14, fontWeight: 600 }}>新增供应商</h4>
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
          >
            <div>
              <label className="config-label">名称 *</label>
              <input
                placeholder="例如：my-openai"
                value={addForm.name}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setAddField("name", e.target.value)
                }
              />
            </div>
            <div>
              <label className="config-label">供应商类型 *</label>
              <select
                value={addForm.provider_type}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setAddField("provider_type", e.target.value)
                }
              >
                {PROVIDER_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="config-label">模型名称</label>
              <input
                placeholder="例如：gpt-4o"
                value={addForm.model_name ?? ""}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setAddField("model_name", e.target.value)
                }
              />
            </div>
            <div>
              <label className="config-label">
                <Key
                  size={12}
                  style={{ marginRight: 4, verticalAlign: "middle" }}
                />
                API Key
              </label>
              <input
                type="password"
                placeholder="sk-..."
                value={addForm.api_key ?? ""}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setAddField("api_key", e.target.value)
                }
              />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label className="config-label">
                <Globe
                  size={12}
                  style={{ marginRight: 4, verticalAlign: "middle" }}
                />
                Base URL（留空使用默认）
              </label>
              <input
                placeholder="例如：https://api.openai.com/v1"
                value={addForm.base_url ?? ""}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setAddField("base_url", e.target.value)
                }
              />
            </div>
          </div>
          <div
            className="row"
            style={{ marginTop: 14, justifyContent: "flex-end" }}
          >
            <button className="btn-secondary" onClick={cancelAdd}>
              <X size={14} />
              取消
            </button>
            <button onClick={onAdd} disabled={addSaving}>
              <Save size={14} />
              {addSaving ? "保存中..." : "添加"}
            </button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loaded && !showAdd && (
        <EmptyState
          icon={<Server size={28} />}
          title="加载供应商配置"
          description="点击刷新查看已配置的供应商，或新增一个"
          action={
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              加载
            </button>
          }
        />
      )}

      {/* Provider list */}
      {loaded && (
        <>
          {providers.length === 0 ? (
            <EmptyState
              icon={<Server size={28} />}
              title="暂无供应商"
              description="点击右上角「新增供应商」添加第一个 LLM 供应商"
            />
          ) : (
            <div className="card-list animate-list">
              {providers.map((p) => (
                <div key={p.name}>
                  {/* Main row */}
                  <div
                    className="data-row"
                    style={
                      p.enabled
                        ? { borderLeft: "3px solid var(--color-brand)" }
                        : undefined
                    }
                  >
                    <div className="data-row-info">
                      <div className="data-row-title">
                        {p.name}
                        <span style={{ marginLeft: 8 }}>
                          <Badge variant="info">{p.provider_type}</Badge>
                        </span>
                        {p.model_name && (
                          <span style={{ marginLeft: 6 }}>
                            <Badge variant="neutral">{p.model_name}</Badge>
                          </span>
                        )}
                        {p.enabled && (
                          <span style={{ marginLeft: 6 }}>
                            <Badge variant="success">已启用</Badge>
                          </span>
                        )}
                      </div>
                      <div
                        className="data-row-meta"
                        style={{ display: "flex", gap: 16, marginTop: 4 }}
                      >
                        {p.api_key && (
                          <span>
                            <Key
                              size={11}
                              style={{
                                marginRight: 3,
                                verticalAlign: "middle",
                              }}
                            />
                            {p.api_key}
                          </span>
                        )}
                        {p.base_url && (
                          <span>
                            <Globe
                              size={11}
                              style={{
                                marginRight: 3,
                                verticalAlign: "middle",
                              }}
                            />
                            {p.base_url}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="data-row-actions" style={{ gap: 8 }}>
                      {/* Enable toggle */}
                      <Toggle
                        checked={!!p.enabled}
                        onChange={() => onToggleEnabled(p)}
                      />
                      {/* Apply to agent */}
                      {p.enabled && (
                        <button
                          className="btn-secondary btn-sm"
                          onClick={() => onApply(p.name)}
                          disabled={applyingName === p.name}
                          title="应用到 Agent（热重载）"
                        >
                          <Play size={13} />
                          {applyingName === p.name ? "应用中..." : "应用"}
                        </button>
                      )}
                      {/* Edit settings */}
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() =>
                          editingName === p.name ? cancelEdit() : startEdit(p)
                        }
                        title="编辑设置"
                      >
                        {editingName === p.name ? (
                          <X size={13} />
                        ) : (
                          <Edit2 size={13} />
                        )}
                      </button>
                      {/* Delete */}
                      <button
                        className="btn-danger btn-sm"
                        onClick={() => onDelete(p.name)}
                        title="删除"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {/* Inline settings form */}
                  {editingName === p.name && (
                    <div
                      className="card"
                      style={{
                        margin: "0 0 4px 0",
                        padding: 16,
                        borderTop: "none",
                        borderRadius: "0 0 8px 8px",
                        background: "var(--color-surface-alt, #f9fafb)",
                      }}
                    >
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 12,
                        }}
                      >
                        <div>
                          <label className="config-label">供应商类型</label>
                          <select
                            value={editForm.provider_type}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                              setEditField("provider_type", e.target.value)
                            }
                          >
                            {PROVIDER_TYPES.map((t) => (
                              <option key={t} value={t}>
                                {t}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="config-label">模型名称</label>
                          <input
                            placeholder="例如：gpt-4o"
                            value={editForm.model_name ?? ""}
                            onChange={(e: ChangeEvent<HTMLInputElement>) =>
                              setEditField("model_name", e.target.value)
                            }
                          />
                        </div>
                        <div>
                          <label className="config-label">
                            <Key
                              size={12}
                              style={{
                                marginRight: 4,
                                verticalAlign: "middle",
                              }}
                            />
                            API Key（留空不修改）
                          </label>
                          <input
                            type="password"
                            placeholder="输入新 Key 覆盖，留空保持不变"
                            value={editForm.api_key ?? ""}
                            onChange={(e: ChangeEvent<HTMLInputElement>) =>
                              setEditField("api_key", e.target.value)
                            }
                          />
                        </div>
                        <div>
                          <label className="config-label">
                            <Globe
                              size={12}
                              style={{
                                marginRight: 4,
                                verticalAlign: "middle",
                              }}
                            />
                            Base URL
                          </label>
                          <input
                            placeholder="留空使用默认"
                            value={editForm.base_url ?? ""}
                            onChange={(e: ChangeEvent<HTMLInputElement>) =>
                              setEditField("base_url", e.target.value)
                            }
                          />
                        </div>
                      </div>
                      <div
                        className="row"
                        style={{ marginTop: 12, justifyContent: "flex-end" }}
                      >
                        <button
                          className="btn-secondary btn-sm"
                          onClick={cancelEdit}
                        >
                          <X size={13} />
                          取消
                        </button>
                        <button
                          className="btn-sm"
                          onClick={() => onSaveEdit(p.name)}
                          disabled={editSaving}
                        >
                          <Save size={13} />
                          {editSaving ? "保存中..." : "保存设置"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
