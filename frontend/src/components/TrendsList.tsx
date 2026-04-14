import { Link } from "react-router-dom";
import type { TrendingEntity } from "../types";
import { EntityTypeBadge } from "./EntityBadge";

interface TrendsListProps {
  trends: TrendingEntity[];
  loading: boolean;
}

export default function TrendsList({ trends, loading }: TrendsListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="skeleton h-4 w-4 rounded-full" />
            <div className="skeleton h-4 flex-1" />
            <div className="skeleton h-5 w-12" />
          </div>
        ))}
      </div>
    );
  }

  if (trends.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-ink-400">No trending entities yet.</p>
        <p className="text-xs text-ink-400 mt-1">Entities will appear here as articles are analyzed.</p>
      </div>
    );
  }

  const maxMentions = Math.max(...trends.map((t) => t.mention_count));

  return (
    <div className="space-y-2">
      {trends.map((trend, index) => {
        const barWidth = (trend.mention_count / maxMentions) * 100;
        const sentimentColor =
          trend.sentiment_avg > 0.2
            ? "text-sage-600"
            : trend.sentiment_avg < -0.2
              ? "text-red-600"
              : "text-ink-500";

        return (
          <Link
            key={trend.entity.id}
            to={`/entities/${trend.entity.id}`}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-ink-50 transition-colors group"
          >
            <span className="text-xs text-ink-400 w-5 text-right font-mono">
              {index + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-ink-800 group-hover:text-accent-600 transition-colors truncate">
                  {trend.entity.name}
                </span>
                <EntityTypeBadge type={trend.entity.type} />
              </div>
              <div className="mt-1 h-1 bg-ink-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent-400 rounded-full transition-all duration-500"
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
            <div className="flex-shrink-0 text-right">
              <p className="text-sm font-semibold text-ink-700 tabular-nums">
                {trend.mention_count}
              </p>
              <p className={`text-xs ${sentimentColor} tabular-nums`}>
                {trend.sentiment_avg >= 0 ? "+" : ""}
                {trend.sentiment_avg.toFixed(2)}
              </p>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
