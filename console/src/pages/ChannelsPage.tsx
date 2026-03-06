import { useEffect, useState } from "react";
import { Radio, RefreshCw } from "lucide-react";
import { getChannels } from "../api";
import type { ChannelItem } from "../types";
import { PageHeader, EmptyState, Badge } from "../components/ui";
import { ChannelGlyph, IconBadge } from "../components/icons";

export default function ChannelsPage() {
  const [channels, setChannels] = useState<ChannelItem[]>([]);
  const [loaded, setLoaded] = useState(false);

  async function onLoad() {
    setChannels(await getChannels());
    setLoaded(true);
  }

  useEffect(() => {
    void onLoad();
  }, []);

  return (
    <div className="panel">
      <PageHeader
        title="频道管理"
        description="查看已注册的通信频道"
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
    </div>
  );
}
