import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import type { DashboardStats, TrendingEntity, ArticleListItem } from "../types";
import { fetchDashboardStats, fetchTrends, fetchArticles } from "../api/client";
import StatsCards from "../components/StatsCards";
import TrendsList from "../components/TrendsList";
import ArticleCard, { ArticleCardSkeleton } from "../components/ArticleCard";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<TrendingEntity[]>([]);
  const [recentArticles, setRecentArticles] = useState<ArticleListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        setLoading(true);
        setError(null);

        const [statsData, trendsData, articlesData] = await Promise.all([
          fetchDashboardStats(),
          fetchTrends(),
          fetchArticles({ limit: 8 }),
        ]);

        if (cancelled) return;

        setStats(statsData);
        setTrends(trendsData);
        setRecentArticles(articlesData.data);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-serif font-bold text-ink-900">Dashboard</h1>
        <p className="mt-1 text-sm text-ink-500">
          Overview of your news intelligence pipeline
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Stats */}
      <StatsCards stats={stats} loading={loading} />

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trending entities */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="px-5 py-4 border-b border-ink-100">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-serif font-semibold text-ink-900">
                  Trending Entities
                </h2>
                <Link to="/entities" className="text-xs text-accent-600 hover:text-accent-700 font-medium">
                  View all
                </Link>
              </div>
              <p className="text-xs text-ink-400 mt-0.5">Most mentioned in the last 7 days</p>
            </div>
            <div className="p-3">
              <TrendsList trends={trends} loading={loading} />
            </div>
          </div>
        </div>

        {/* Recent articles */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="px-5 py-4 border-b border-ink-100">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-serif font-semibold text-ink-900">
                  Recent Articles
                </h2>
                <Link to="/articles" className="text-xs text-accent-600 hover:text-accent-700 font-medium">
                  View all
                </Link>
              </div>
            </div>
            <div className="divide-y divide-ink-100">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="px-1">
                    <ArticleCardSkeleton />
                  </div>
                ))
              ) : recentArticles.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-sm text-ink-400">No articles ingested yet.</p>
                  <p className="text-xs text-ink-400 mt-1">
                    Add a news source to get started.
                  </p>
                </div>
              ) : (
                recentArticles.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
