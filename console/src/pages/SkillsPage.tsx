import { useEffect, useState } from "react";
import { Puzzle, RefreshCw } from "lucide-react";
import {
  listSkills,
  listActiveSkills,
  enableSkill,
  disableSkill,
} from "../api";
import type { SkillItem } from "../types";
import {
  PageHeader,
  EmptyState,
  Badge,
  Toggle,
  MetricPill,
  NoticeBanner,
  SurfaceCard,
} from "../components/ui";

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [active, setActive] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");

  async function onLoad() {
    setSkills(await listSkills());
    setActive(await listActiveSkills());
    setLoaded(true);
  }

  useEffect(() => {
    void onLoad();
  }, []);

  async function onToggle(skillName: string, isActive: boolean) {
    if (isActive) {
      await disableSkill(skillName);
      setNotice(`已禁用技能 ${skillName}`);
    } else {
      await enableSkill(skillName);
      setNotice(`已启用技能 ${skillName}`);
    }
    await onLoad();
  }

  const filteredSkills = skills.filter((skill, idx) => {
    const skillName = skill.name || `skill-${idx}`;
    return `${skillName} ${skill.description || ""}`
      .toLowerCase()
      .includes(query.trim().toLowerCase());
  });

  return (
    <div className="panel">
      <PageHeader
        eyebrow="Capability Switches"
        title="技能管理"
        description="启用或禁用 Agent 技能，同时影响聊天和 `task_type=agent` 的定时任务。"
        meta={
          <div className="page-header-meta-row">
            <MetricPill label="技能总数" value={skills.length} />
            <MetricPill label="已启用" value={active.length} />
          </div>
        }
        actions={
          <div className="toolbar-row">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索技能名称或描述"
            />
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              刷新技能
            </button>
          </div>
        }
      />

      {notice && <NoticeBanner variant="success">{notice}</NoticeBanner>}

      {!loaded && skills.length === 0 && (
        <EmptyState
          icon={<Puzzle size={28} />}
          title="加载技能列表"
          description="管理 Agent 可用的技能和能力"
          action={
            <button onClick={onLoad}>
              <RefreshCw size={15} />
              加载
            </button>
          }
        />
      )}

      <SurfaceCard
        title="技能开关"
        description="建议只启用你当前需要的能力，避免让 Agent 在低价值技能上分散注意力。"
      >
        <div className="card-list animate-list">
          {filteredSkills.length === 0 && (
            <div className="empty-inline">当前筛选条件下没有匹配技能</div>
          )}
          {filteredSkills.map((skill: SkillItem, idx: number) => {
            const skillName = skill.name || `skill-${idx}`;
            const isActive = active.includes(skillName);
            return (
              <div key={skillName} className="data-row">
                <div className="data-row-info">
                  <div className="data-row-title">
                    <Puzzle
                      size={14}
                      style={{ marginRight: 6, verticalAlign: "middle" }}
                    />
                    {skillName}
                    {isActive ? (
                      <Badge variant="success">已启用</Badge>
                    ) : (
                      <Badge variant="neutral">已禁用</Badge>
                    )}
                  </div>
                  {skill.description && (
                    <div className="data-row-meta">{skill.description}</div>
                  )}
                </div>
                <div className="data-row-actions">
                  <Toggle
                    checked={isActive}
                    onChange={() => onToggle(skillName, isActive)}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </SurfaceCard>
    </div>
  );
}
