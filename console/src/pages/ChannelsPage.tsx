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
import { PageHeader, EmptyState, Badge } from "../components/ui";
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
      await onLoad();
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
      await onLoad();
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    void onLoad();
  }, []);

  return (
    <div className="panel">
      <PageHeader
        title="频道管理"
        description="查看已注册频道，并管理账号映射与自定义插件"
        actions={
          <button onClick={onLoad}>
            <RefreshCw size={15} />
            刷新频道
          </button>
        }
      />

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

      <div className="card-list animate-list">
        {channels.map((item: ChannelItem, idx: number) => (
          <div key={idx} className="data-row">
            <div className="data-row-info">
              <div className="data-row-title">
                <ChannelGlyph channel={item.name} />
                {item.name}
              </div>
            </div>
            <div className="data-row-actions">
              <Badge variant="info">{item.type}</Badge>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        <h3 style={{ margin: "8px 0" }}>频道目录</h3>
        <div className="card-list animate-list">
          {catalog.map((item: any) => (
            <div key={String(item.key)} className="data-row">
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
      </div>

      <div style={{ marginTop: 16 }}>
        <h3 style={{ margin: "8px 0" }}>自定义频道插件</h3>
        <div style={{ display: "grid", gap: 8 }}>
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
        <div className="card-list animate-list" style={{ marginTop: 8 }}>
          {customChannels.map((item: any) => (
            <div key={String(item.key)} className="data-row">
              <div className="data-row-info">
                <div className="data-row-title">{String(item.key)}</div>
                <div className="hint">{String(item.path || "")}</div>
              </div>
              <div className="data-row-actions">
                <button
                  onClick={async () => {
                    await removeCustomChannel(String(item.key));
                    await onLoad();
                  }}
                >
                  <Trash2 size={14} />
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <h3 style={{ margin: "8px 0" }}>账号与绑定配置</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <label className="hint">channel_accounts (JSON)</label>
          <textarea
            className="pre"
            style={{ minHeight: 180 }}
            value={accountsJson}
            onChange={(e) => setAccountsJson(e.target.value)}
          />
          <label className="hint">bindings (JSON)</label>
          <textarea
            className="pre"
            style={{ minHeight: 140 }}
            value={bindingsJson}
            onChange={(e) => setBindingsJson(e.target.value)}
          />
          <button onClick={onSaveAccountsAndBindings} disabled={saving}>
            <Save size={15} />
            保存并热重载
          </button>
        </div>
      </div>
    </div>
  );
}
