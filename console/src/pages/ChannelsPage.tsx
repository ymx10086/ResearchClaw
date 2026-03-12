import { useEffect, useState } from "react";
import { Plug, Radio, RefreshCw, Save, Trash2 } from "lucide-react";
import {
  getBindings,
  getChannelAccounts,
  getChannelCatalog,
  getChannels,
  installCustomChannel,
  listCustomChannels,
  removeCustomChannel,
  updateBindings,
  updateChannelAccounts,
} from "../api";
import type { ChannelItem } from "../types";
import {
  Badge,
  EmptyState,
  MetricPill,
  NoticeBanner,
  PageHeader,
  SurfaceCard,
} from "../components/ui";
import { ChannelGlyph, IconBadge } from "../components/icons";

export default function ChannelsPage() {
  const [channels, setChannels] = useState<ChannelItem[]>([]);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [customChannels, setCustomChannels] = useState<any[]>([]);
  const [accountsJson, setAccountsJson] = useState<string>("{}");
  const [bindingsJson, setBindingsJson] = useState<string>("[]");
  const [installKey, setInstallKey] = useState<string>("");
  const [installPath, setInstallPath] = useState<string>("");
  const [installUrl, setInstallUrl] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState<{
    variant: "success" | "danger" | "warning" | "info";
    text: string;
  } | null>(null);

  async function onLoad() {
    const [rows, cat, custom, accounts, bindings] = await Promise.all([
      getChannels(),
      getChannelCatalog(),
      listCustomChannels(),
      getChannelAccounts(),
      getBindings(),
    ]);
    setChannels(rows);
    setCatalog(Array.isArray(cat?.channels) ? cat.channels : []);
    setCustomChannels(Array.isArray(custom) ? custom : []);
    setAccountsJson(JSON.stringify(accounts || {}, null, 2));
    setBindingsJson(JSON.stringify(bindings || [], null, 2));
    setLoaded(true);
  }

  async function onSaveAccountsAndBindings() {
    setSaving(true);
    try {
      const parsedAccounts = JSON.parse(accountsJson || "{}");
      const parsedBindings = JSON.parse(bindingsJson || "[]");
      await updateChannelAccounts(parsedAccounts);
      await updateBindings(Array.isArray(parsedBindings) ? parsedBindings : []);
      setNotice({ variant: "success", text: "账号与绑定配置已保存" });
      await onLoad();
    } catch (error: any) {
      setNotice({
        variant: "danger",
        text: error?.message || "保存账号与绑定配置失败",
      });
    } finally {
      setSaving(false);
    }
  }

  async function onInstallCustom() {
    setSaving(true);
    try {
      await installCustomChannel({
        key: installKey.trim(),
        path: installPath.trim() || undefined,
        url: installUrl.trim() || undefined,
        overwrite: true,
      });
      setInstallPath("");
      setInstallUrl("");
      setNotice({ variant: "success", text: "自定义频道插件已安装/更新" });
      await onLoad();
    } catch (error: any) {
      setNotice({
        variant: "danger",
        text: error?.message || "安装自定义频道失败",
      });
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    void onLoad();
  }, []);

  const queryText = query.trim().toLowerCase();
  const filteredChannels = channels.filter((item) =>
    `${item.name} ${item.type}`.toLowerCase().includes(queryText),
  );
  const filteredCatalog = catalog.filter((item) =>
    `${String(item.key)} ${item.builtin ? "builtin" : "custom"}`
      .toLowerCase()
      .includes(queryText),
  );
  const filteredCustom = customChannels.filter((item) =>
    `${String(item.key)} ${String(item.path || "")}`
      .toLowerCase()
      .includes(queryText),
  );

  return (
    <div className="panel">
      <PageHeader
        eyebrow="Multi-channel Ingress"
        title="频道管理"
        description="把内建频道、自定义插件、账号映射和路由绑定放在同一控制面里管理。"
        meta={
          <div className="page-header-meta-row">
            <MetricPill label="已注册" value={channels.length} />
            <MetricPill label="目录总数" value={catalog.length} />
            <MetricPill label="自定义插件" value={customChannels.length} />
          </div>
        }
        actions={
          <div className="toolbar-row">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索频道 / 目录 / 插件"
            />
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              刷新频道
            </button>
          </div>
        }
      />

      {notice && (
        <NoticeBanner variant={notice.variant}>{notice.text}</NoticeBanner>
      )}

      {!loaded && channels.length === 0 && (
        <EmptyState
          icon={
            <IconBadge tone="blue">
              <Radio size={20} />
            </IconBadge>
          }
          title="点击刷新加载频道"
          description="查看所有已注册的通信频道信息"
          action={
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              加载
            </button>
          }
        />
      )}

      <div className="dashboard-grid">
        <SurfaceCard
          title="已注册频道"
          description="运行时真正可用的入口，适合先看状态和类型。"
          className="span-7"
        >
          <div className="card-list animate-list">
            {filteredChannels.length === 0 && (
              <div className="empty-inline">当前筛选条件下没有匹配频道</div>
            )}
            {filteredChannels.map((item: ChannelItem, idx: number) => (
              <div key={idx} className="data-row">
                <div className="data-row-info">
                  <div className="data-row-title">
                    <ChannelGlyph channel={item.name} />
                    {item.name}
                  </div>
                  <div className="data-row-meta">
                    当前实例已经注册到运行时消息分发链路。
                  </div>
                </div>
                <div className="data-row-actions">
                  <Badge variant="info">{item.type}</Badge>
                </div>
              </div>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard
          title="频道目录"
          description="内建与外部插件的统一目录，方便确认装载来源。"
          className="span-5"
        >
          <div className="card-list animate-list">
            {filteredCatalog.length === 0 && (
              <div className="empty-inline">当前筛选条件下没有匹配目录项</div>
            )}
            {filteredCatalog.map((item: any) => (
              <div key={String(item.key)} className="data-row compact">
                <div className="data-row-info">
                  <div className="data-row-title">
                    <ChannelGlyph channel={String(item.key)} />
                    {String(item.key)}
                  </div>
                </div>
                <div className="data-row-actions">
                  <Badge variant={item.builtin ? "info" : "warning"}>
                    {item.builtin ? "builtin" : "custom"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard
          title="安装自定义频道"
          description="可从本地路径或远程 URL 安装/更新，适合接 webhook、企业 IM 或自定义消息入口。"
          className="span-5"
        >
          <div className="form-stack">
            <input
              placeholder="channel key (e.g. webhook)"
              value={installKey}
              onChange={(e) => setInstallKey(e.target.value)}
            />
            <input
              placeholder="local path (optional)"
              value={installPath}
              onChange={(e) => setInstallPath(e.target.value)}
            />
            <input
              placeholder="remote url (optional)"
              value={installUrl}
              onChange={(e) => setInstallUrl(e.target.value)}
            />
            <button
              onClick={onInstallCustom}
              disabled={saving || !installKey.trim()}
            >
              <Plug size={15} />
              安装/更新插件
            </button>
          </div>

          <div className="card-list animate-list mt-4">
            {filteredCustom.length === 0 && (
              <div className="empty-inline">
                {customChannels.length === 0
                  ? "暂无自定义插件"
                  : "当前筛选条件下没有匹配插件"}
              </div>
            )}
            {filteredCustom.map((item: any) => (
              <div key={String(item.key)} className="data-row compact">
                <div className="data-row-info">
                  <div className="data-row-title">{String(item.key)}</div>
                  <div className="data-row-meta">{String(item.path || "")}</div>
                </div>
                <div className="data-row-actions">
                  <button
                    className="btn-secondary btn-sm"
                    onClick={async () => {
                      if (
                        !window.confirm(`确认删除插件 ${String(item.key)} 吗？`)
                      ) {
                        return;
                      }
                      try {
                        await removeCustomChannel(String(item.key));
                        setNotice({
                          variant: "success",
                          text: `已删除插件 ${String(item.key)}`,
                        });
                        await onLoad();
                      } catch (error: any) {
                        setNotice({
                          variant: "danger",
                          text: error?.message || "删除自定义频道失败",
                        });
                      }
                    }}
                  >
                    <Trash2 size={14} />
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard
          title="账号与绑定配置"
          description="账号实例和 bindings 直接影响消息路由，保存后会热重载到运行时。"
          className="span-7"
          actions={
            <button onClick={onSaveAccountsAndBindings} disabled={saving}>
              <Save size={15} />
              保存并热重载
            </button>
          }
        >
          <div className="config-grid">
            <div className="code-editor-card">
              <label className="hint">channel_accounts (JSON)</label>
              <textarea
                className="pre"
                style={{ minHeight: 260 }}
                value={accountsJson}
                onChange={(e) => setAccountsJson(e.target.value)}
              />
            </div>
            <div className="code-editor-card">
              <label className="hint">bindings (JSON)</label>
              <textarea
                className="pre"
                style={{ minHeight: 260 }}
                value={bindingsJson}
                onChange={(e) => setBindingsJson(e.target.value)}
              />
            </div>
          </div>
        </SurfaceCard>
      </div>
    </div>
  );
}
