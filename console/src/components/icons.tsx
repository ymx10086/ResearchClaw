import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Bot,
  Cable,
  MessageCircle,
  MessageSquare,
  Phone,
  Radio,
  Send,
  Smartphone,
  Terminal,
} from "lucide-react";

type IconTone =
  | "brand"
  | "teal"
  | "blue"
  | "amber"
  | "green"
  | "violet"
  | "slate"
  | "danger";

export function IconBadge({
  children,
  tone = "brand",
  size = "md",
  className = "",
}: {
  children: ReactNode;
  tone?: IconTone;
  size?: "sm" | "md";
  className?: string;
}) {
  return (
    <span className={`icon-badge ${size} tone-${tone} ${className}`.trim()}>
      {children}
    </span>
  );
}

type ChannelMeta = {
  Icon: LucideIcon;
  tone: IconTone;
};

const CHANNEL_META: Record<string, ChannelMeta> = {
  console: { Icon: Terminal, tone: "slate" },
  dingtalk: { Icon: MessageSquare, tone: "blue" },
  feishu: { Icon: Send, tone: "teal" },
  telegram: { Icon: Send, tone: "blue" },
  discord: { Icon: MessageCircle, tone: "violet" },
  discord_: { Icon: MessageCircle, tone: "violet" },
  imessage: { Icon: Smartphone, tone: "green" },
  qq: { Icon: Bot, tone: "amber" },
  voice: { Icon: Phone, tone: "teal" },
  mcp: { Icon: Cable, tone: "brand" },
};

export function ChannelGlyph({
  channel,
  size = 14,
}: {
  channel?: string;
  size?: number;
}) {
  const key = (channel || "").toLowerCase();
  const meta = CHANNEL_META[key] ?? { Icon: Radio, tone: "brand" as IconTone };
  const Icon = meta.Icon;
  return (
    <IconBadge tone={meta.tone} size="sm" className="channel-glyph">
      <Icon size={size} />
    </IconBadge>
  );
}
