import { Link } from "react-router-dom";
import type { ArticleListItem } from "../types";

interface ArticleCardProps {
  article: ArticleListItem;
}

export default function ArticleCard({ article }: ArticleCardProps) {
  const date = new Date(article.published_at);
  const formattedDate = date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const timeAgo = getTimeAgo(date);

  return (
    <Link to={`/articles/${article.id}`} className="card-hover block p-4 group">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-ink-900 group-hover:text-accent-600 transition-colors line-clamp-2">
            {article.title}
          </h3>
          <div className="mt-2 flex items-center gap-3 text-xs text-ink-500">
            <span className="inline-flex items-center gap-1">
              <SourceIcon className="w-3.5 h-3.5" />
              {article.source.name}
            </span>
            <span title={formattedDate}>{timeAgo}</span>
          </div>
        </div>
        <div className="flex-shrink-0 mt-0.5">
          {article.analyzed ? (
            <span className="badge bg-sage-100 text-sage-700">Analyzed</span>
          ) : (
            <span className="badge bg-ink-100 text-ink-500">Pending</span>
          )}
        </div>
      </div>
    </Link>
  );
}

export function ArticleCardSkeleton() {
  return (
    <div className="card p-4">
      <div className="skeleton h-4 w-3/4 mb-2" />
      <div className="skeleton h-4 w-1/2 mb-3" />
      <div className="flex gap-3">
        <div className="skeleton h-3 w-20" />
        <div className="skeleton h-3 w-16" />
      </div>
    </div>
  );
}

function SourceIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function getTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
