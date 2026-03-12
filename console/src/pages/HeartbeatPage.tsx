import { useEffect, useState } from "react";
import { Heart, RefreshCw } from "lucide-react";
import { getHeartbeat } from "../api";
import {
  EmptyState,
  MetricPill,
  PageHeader,
  SurfaceCard,
} from "../components/ui";

export default function HeartbeatPage() {
  const [heartbeat, setHeartbeat] = useState<any>(null);
  const [loaded, setLoaded] = useState(false);

  async function onLoad() {
    setHeartbeat(await getHeartbeat());
    setLoaded(true);
  }

  useEffect(() => {
    void onLoad();
  }, []);

  return (
    <div className="panel">
      <PageHeader
        eyebrow="Liveness Check"
        title="心跳检测"
        description="查看心跳任务的当前配置与运行状态，确认系统是否会按周期自动唤醒。"
        meta={
          <div className="page-header-meta-row">
            <MetricPill
              label="启用"
              value={heartbeat?.enabled ? "Yes" : loaded ? "No" : "-"}
            />
            <MetricPill label="频率" value={heartbeat?.every || "-"} />
          </div>
        }
        actions={
          <button onClick={onLoad}>
            <RefreshCw size={15} />
            刷新心跳
          </button>
        }
      />

      {!loaded && !heartbeat && (
        <EmptyState
          icon={<Heart size={28} />}
          title="检测系统心跳"
          description="点击刷新查看各组件的实时状态"
          action={
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              加载
            </button>
          }
        />
      )}

      {heartbeat && (
        <SurfaceCard
          title="Heartbeat 配置"
          description="当前返回的是运行时心跳配置的原始结构，适合排查调度目标与参数。"
        >
          <pre className="pre">{JSON.stringify(heartbeat, null, 2)}</pre>
        </SurfaceCard>
      )}
    </div>
  );
}
