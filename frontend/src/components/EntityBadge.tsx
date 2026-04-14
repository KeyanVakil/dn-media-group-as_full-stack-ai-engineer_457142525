import type { EntityType } from "../types";

interface EntityBadgeProps {
  type: EntityType;
  name?: string;
  sentiment?: number;
  size?: "sm" | "md";
  clickable?: boolean;
  onClick?: () => void;
}

const typeConfig: Record<EntityType, { label: string; bg: string; text: string; dot: string }> = {
  person: {
    label: "Person",
    bg: "bg-accent-50",
    text: "text-accent-700",
    dot: "bg-accent-500",
  },
  company: {
    label: "Company",
    bg: "bg-rust-50",
    text: "text-rust-700",
    dot: "bg-rust-500",
  },
  location: {
    label: "Location",
    bg: "bg-sage-50",
    text: "text-sage-700",
    dot: "bg-sage-500",
  },
  topic: {
    label: "Topic",
    bg: "bg-purple-50",
    text: "text-purple-700",
    dot: "bg-purple-500",
  },
  event: {
    label: "Event",
    bg: "bg-amber-50",
    text: "text-amber-700",
    dot: "bg-amber-500",
  },
};

export function getEntityColor(type: EntityType): string {
  const colors: Record<EntityType, string> = {
    person: "#3996f6",
    company: "#ee7122",
    location: "#34985f",
    topic: "#8b5cf6",
    event: "#f59e0b",
  };
  return colors[type];
}

export default function EntityBadge({ type, name, sentiment, size = "sm", clickable, onClick }: EntityBadgeProps) {
  const config = typeConfig[type];
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";

  const sentimentIndicator = sentiment !== undefined ? (
    <span
      className={`w-1.5 h-1.5 rounded-full ${
        sentiment > 0.2 ? "bg-sage-500" : sentiment < -0.2 ? "bg-red-500" : "bg-ink-400"
      }`}
      title={`Sentiment: ${sentiment.toFixed(2)}`}
    />
  ) : null;

  const Component = clickable ? "button" : "span";

  return (
    <Component
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${config.bg} ${config.text} ${sizeClasses} ${
        clickable ? "cursor-pointer hover:opacity-80 transition-opacity" : ""
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {name || config.label}
      {sentimentIndicator}
    </Component>
  );
}

export function EntityTypeBadge({ type }: { type: EntityType }) {
  const config = typeConfig[type];
  return (
    <span className={`badge ${config.bg} ${config.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot} mr-1`} />
      {config.label}
    </span>
  );
}
