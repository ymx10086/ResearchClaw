import type { LucideProps } from "lucide-react";
import {
  Search,
  BookMarked,
  FlaskConical,
  MessageSquare,
  Puzzle,
  Lock,
} from "lucide-react";
import { motion } from "motion/react";
import { t, type Lang } from "../i18n";

const items: Array<{
  key: string;
  icon: React.ComponentType<LucideProps>;
}> = [
  { key: "papers", icon: Search },
  { key: "references", icon: BookMarked },
  { key: "analysis", icon: FlaskConical },
  { key: "channels", icon: MessageSquare },
  { key: "skills", icon: Puzzle },
  { key: "private", icon: Lock },
];

interface FeaturesProps {
  lang: Lang;
  delay?: number;
}

export function Features({ lang, delay = 0 }: FeaturesProps) {
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
          margin: "0 0 var(--space-5)",
          fontSize: "1.375rem",
          fontWeight: 600,
          color: "var(--text)",
        }}
      >
        {t(lang, "features.title")}
      </h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(16rem, 1fr))",
          gap: "var(--space-4)",
        }}
      >
        {items.map(({ key, icon: Icon }) => (
          <div
            key={key}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "0.5rem",
              padding: "var(--space-4)",
            }}
          >
            <div
              style={{
                marginBottom: "var(--space-2)",
                color: "var(--text)",
              }}
            >
              <Icon size={22} strokeWidth={1.5} aria-hidden />
            </div>
            <h3
              style={{
                margin: "0 0 var(--space-1)",
                fontSize: "1rem",
                fontWeight: 600,
                color: "var(--text)",
              }}
            >
              {t(lang, `features.${key}.title`)}
            </h3>
            <p
              style={{
                margin: 0,
                fontSize: "0.875rem",
                lineHeight: 1.55,
                color: "var(--text-muted)",
              }}
            >
              {t(lang, `features.${key}.desc`)}
            </p>
          </div>
        ))}
      </div>
    </motion.section>
  );
}
