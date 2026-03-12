import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import { Download, Save, Settings, SlidersHorizontal } from "lucide-react";
import { getAgentRunningConfig, updateAgentRunningConfig } from "../api";
import type { AgentRunningConfig } from "../types";
import { MetricPill, PageHeader, SurfaceCard } from "../components/ui";

export default function AgentConfigPage() {
  const [config, setConfig] = useState<AgentRunningConfig>({
    max_iters: 50,
    max_input_length: 128000,
  });
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);

  async function onLoad() {
    setConfig(await getAgentRunningConfig());
    setLoaded(true);
  }

  useEffect(() => {
    void onLoad();
  }, []);

  async function onSave() {
    setSaving(true);
    try {
      await updateAgentRunningConfig(config);
      await onLoad();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel">
      <PageHeader
        eyebrow="Runtime Tuning"
        title="Agent 配置"
        description="把高频运行参数放在一处调优，平衡推理深度、上下文长度和交互速度。"
        meta={
          <div className="page-header-meta-row">
            <MetricPill label="最大迭代" value={config.max_iters} />
            <MetricPill label="上下文上限" value={config.max_input_length} />
          </div>
        }
        actions={
          <div className="row">
            <button className="btn-secondary" onClick={onLoad}>
              <Download size={15} />
              {loaded ? "重新加载" : "加载配置"}
            </button>
            <button onClick={onSave} disabled={saving}>
              <Save size={15} />
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        }
      />

      {!loaded ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <Settings size={28} />
          </div>
          <h3>加载 Agent 配置</h3>
          <p>点击上方加载按钮获取当前配置</p>
          <div className="mt-3">
            <button onClick={onLoad}>
              <Download size={15} />
              加载
            </button>
          </div>
        </div>
      ) : (
        <div className="dashboard-grid">
          <SurfaceCard
            title="推理步数"
            description="适合控制任务深度。数值越高，复杂任务成功率更高，但成本和时延也会上升。"
            className="span-6"
          >
            <div className="config-card refined">
              <div className="config-label">
                <SlidersHorizontal
                  size={14}
                  style={{ marginRight: 6, verticalAlign: "middle" }}
                />
                最大迭代次数
              </div>
              <div className="config-desc">Agent 单次任务的最大推理步数</div>
              <input
                type="number"
                value={config.max_iters}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setConfig((prev: AgentRunningConfig) => ({
                    ...prev,
                    max_iters: Number(e.target.value) || 1,
                  }))
                }
              />
            </div>
          </SurfaceCard>

          <SurfaceCard
            title="上下文容量"
            description="适合控制单次任务能容纳的上下文长度，直接影响长论文和长工具输出的可处理范围。"
            className="span-6"
          >
            <div className="config-card refined">
              <div className="config-label">
                <SlidersHorizontal
                  size={14}
                  style={{ marginRight: 6, verticalAlign: "middle" }}
                />
                最大输入长度
              </div>
              <div className="config-desc">单次输入的最大 token 数量</div>
              <input
                type="number"
                value={config.max_input_length}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setConfig((prev: AgentRunningConfig) => ({
                    ...prev,
                    max_input_length: Number(e.target.value) || 1000,
                  }))
                }
              />
            </div>
          </SurfaceCard>
        </div>
      )}
    </div>
  );
}
