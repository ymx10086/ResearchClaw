import type { LucideProps } from "lucide-react";
import {
  MessageSquare,
  CalendarClock,
  Puzzle,
  Code2,
  Server,
  Zap,
} from "lucide-react";
import { motion } from "motion/react";
import { t, type Lang } from "../i18n";

const ITEMS: Array<{
  key: string;
  icon: React.ComponentType<LucideProps>;
  labelZh: string;
  labelEn: string;
}> = [
  {
    key: "imessage",
    icon: MessageSquare,
    labelZh: "iMessage",
    labelEn: "iMessage",
  },
  {
    key: "discord",
    icon: MessageSquare,
    labelZh: "Discord",
    labelEn: "Discord",
  },
  {
    key: "dingtalk",
    icon: MessageSquare,
    labelZh: "钉钉",
    labelEn: "DingTalk",
  },
  { key: "feishu", icon: MessageSquare, labelZh: "飞书", labelEn: "Feishu" },
  { key: "qq", icon: MessageSquare, labelZh: "QQ", labelEn: "QQ" },
  { key: "python", icon: Code2, labelZh: "Python", labelEn: "Python" },
  { key: "cron", icon: CalendarClock, labelZh: "Cron", labelEn: "Cron" },
  { key: "api", icon: Server, labelZh: "HTTP API", labelEn: "HTTP API" },
  { key: "skills", icon: Zap, labelZh: "Skills", labelEn: "Skills" },
  { key: "arxiv", icon: Puzzle, labelZh: "ArXiv", labelEn: "ArXiv" },
];

interface EcosystemProps {
  lang: Lang;
  delay?: number;
}

export function Ecosystem({ lang, delay = 0 }: EcosystemProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      style={{
        margin: "0 auto",
        maxWidth: "var(--container)",
        padding: "var(--space-6) var(--space-4)",
        textAlign: "center",
      }}
    >
      <h2
        style={{
          margin: "0 0 var(--space-1)",
          fontSize: "1.375rem",
          fontWeight: 600,
          color: "var(--text)",
        }}
      >
        {t(lang, "ecosystem.title")}
      </h2>
      <p
        style={{
          margin: "0 0 var(--space-5)",
          fontSize: "0.9375rem",
          color: "var(--text-muted)",
        }}
      >
        {t(lang, "ecosystem.sub")}
      </p>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "var(--space-2)",
        }}
      >
        {ITEMS.map(({ key, icon: Icon, labelZh, labelEn }) => (
          <span
            key={key}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-1)",
              padding: "var(--space-1) var(--space-2)",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "9999px",
              fontSize: "0.875rem",
              color: "var(--text)",
            }}
          >
            <Icon size={16} strokeWidth={1.5} aria-hidden />
            {lang === "zh" ? labelZh : labelEn}
          </span>
        ))}
      </div>
    </motion.section>
  );
}
