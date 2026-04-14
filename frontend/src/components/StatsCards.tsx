import type { DashboardStats } from "../types";

interface StatsCardsProps {
  stats: DashboardStats | null;
  loading: boolean;
}

const statConfig = [
  { key: "total_articles" as const, label: "Total Articles", icon: ArticlesIcon, color: "accent" },
  { key: "articles_analyzed" as const, label: "Analyzed", icon: AnalyzedIcon, color: "sage" },
  { key: "total_entities" as const, label: "Entities Tracked", icon: EntitiesIcon, color: "rust" },
  { key: "total_sources" as const, label: "News Sources", icon: SourcesIcon, color: "accent" },
  { key: "research_tasks_completed" as const, label: "Research Tasks", icon: ResearchIcon, color: "sage" },
];

const colorMap: Record<string, { bg: string; text: string; iconBg: string }> = {
  accent: { bg: "bg-accent-50", text: "text-accent-700", iconBg: "bg-accent-100" },
  sage: { bg: "bg-sage-50", text: "text-sage-700", iconBg: "bg-sage-100" },
  rust: { bg: "bg-rust-50", text: "text-rust-700", iconBg: "bg-rust-100" },
};

export default function StatsCards({ stats, loading }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
      {statConfig.map(({ key, label, icon: Icon, color }) => {
        const colors = colorMap[color];
        return (
          <div key={key} className="card p-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg ${colors.iconBg} ${colors.text} flex items-center justify-center`}>
                <Icon className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-ink-500 font-medium truncate">{label}</p>
                {loading ? (
                  <div className="skeleton h-7 w-16 mt-0.5" />
                ) : (
                  <p className="text-2xl font-semibold text-ink-900 tabular-nums">
                    {stats ? stats[key].toLocaleString() : "--"}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Icon Components ────────────────────────────────────────────────

function ArticlesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function AnalyzedIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 11 12 14 22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  );
}

function EntitiesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function SourcesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function ResearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  );
}
