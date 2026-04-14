import { useState, useEffect, useCallback } from "react";
import type { ArticleListItem, Source } from "../types";
import { fetchArticles, fetchSources, type ArticleFilters } from "../api/client";
import ArticleCard, { ArticleCardSkeleton } from "../components/ArticleCard";

const PAGE_SIZE = 20;

export default function Articles() {
  const [articles, setArticles] = useState<ArticleListItem[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [searchDebounce, setSearchDebounce] = useState("");

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounce(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Load sources
  useEffect(() => {
    fetchSources().then(setSources).catch(() => {});
  }, []);

  // Load articles
  const loadArticles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const filters: ArticleFilters = {
        limit: PAGE_SIZE,
        offset,
        search: searchDebounce || undefined,
        source_id: sourceFilter || undefined,
      };

      const result = await fetchArticles(filters);
      setArticles(result.data);
      setTotal(result.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load articles");
    } finally {
      setLoading(false);
    }
  }, [offset, searchDebounce, sourceFilter]);

  useEffect(() => {
    setOffset(0);
  }, [searchDebounce, sourceFilter]);

  useEffect(() => {
    loadArticles();
  }, [loadArticles]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-serif font-bold text-ink-900">Articles</h1>
        <p className="mt-1 text-sm text-ink-500">
          Browse and search ingested news articles
        </p>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-400" />
              <input
                type="text"
                placeholder="Search articles..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-9"
              />
            </div>
          </div>
          <div className="w-48">
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="input"
            >
              <option value="">All Sources</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Article list */}
      <div className="card divide-y divide-ink-100">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="px-1">
              <ArticleCardSkeleton />
            </div>
          ))
        ) : articles.length === 0 ? (
          <div className="text-center py-16">
            <EmptyIcon className="w-12 h-12 text-ink-300 mx-auto" />
            <p className="text-sm text-ink-500 mt-3">No articles found</p>
            <p className="text-xs text-ink-400 mt-1">
              {search || sourceFilter
                ? "Try adjusting your filters"
                : "Ingest news sources to see articles here"}
            </p>
          </div>
        ) : (
          articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-ink-500">
            Showing {offset + 1}--{Math.min(offset + PAGE_SIZE, total)} of {total}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="btn-secondary text-xs px-3 py-1.5"
            >
              Previous
            </button>
            <span className="text-sm text-ink-600 tabular-nums">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
              className="btn-secondary text-xs px-3 py-1.5"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Icons ──────────────────────────────────────────────────────────

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function EmptyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  );
}
