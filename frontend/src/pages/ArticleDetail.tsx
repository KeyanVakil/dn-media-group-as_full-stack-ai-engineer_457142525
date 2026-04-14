import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import type { ArticleDetail as ArticleDetailType } from "../types";
import { fetchArticle, analyzeArticle } from "../api/client";
import EntityBadge from "../components/EntityBadge";

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [article, setArticle] = useState<ArticleDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchArticle(id!);
        if (!cancelled) setArticle(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load article");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function handleAnalyze() {
    if (!id) return;
    try {
      setAnalyzing(true);
      await analyzeArticle(id);
      // Reload article to get new analysis
      const data = await fetchArticle(id);
      setArticle(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 max-w-4xl">
        <div className="skeleton h-8 w-2/3" />
        <div className="skeleton h-4 w-48" />
        <div className="space-y-3 mt-8">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton h-4 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="text-center py-20">
        <p className="text-lg text-ink-600">{error || "Article not found"}</p>
        <button onClick={() => navigate(-1)} className="btn-secondary mt-4">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-ink-400">
        <Link to="/articles" className="hover:text-accent-600 transition-colors">
          Articles
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-ink-600 truncate max-w-md">{article.title}</span>
      </nav>

      {/* Title & meta */}
      <header>
        <h1 className="text-3xl font-serif font-bold text-ink-900 leading-tight">
          {article.title}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-ink-500">
          <span className="font-medium text-ink-700">{article.source.name}</span>
          {article.author && <span>By {article.author}</span>}
          <span>
            {new Date(article.published_at).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </span>
        </div>
      </header>

      {/* AI Summary */}
      {article.summary ? (
        <div className="card border-accent-200 bg-accent-50/30">
          <div className="px-5 py-4 border-b border-accent-100">
            <h2 className="text-sm font-semibold text-accent-700 uppercase tracking-wider flex items-center gap-2">
              <SparklesIcon className="w-4 h-4" />
              AI Summary
            </h2>
          </div>
          <div className="p-5 space-y-4">
            <p className="text-sm text-ink-700 leading-relaxed">
              {article.summary.summary}
            </p>

            {/* Topics */}
            {article.summary.topics.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-ink-500 uppercase tracking-wider mb-2">
                  Topics
                </h3>
                <div className="flex flex-wrap gap-2">
                  {article.summary.topics.map((topic) => (
                    <span key={topic} className="badge bg-accent-100 text-accent-700">
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Key Facts */}
            {article.summary.key_facts.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-ink-500 uppercase tracking-wider mb-2">
                  Key Facts
                </h3>
                <ul className="space-y-1.5">
                  {article.summary.key_facts.map((fact, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-ink-600">
                      <span className="text-accent-400 mt-0.5 flex-shrink-0">&#9670;</span>
                      {fact}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="card p-5 text-center">
          <p className="text-sm text-ink-400 mb-3">This article has not been analyzed yet.</p>
          <button onClick={handleAnalyze} disabled={analyzing} className="btn-primary">
            {analyzing ? (
              <>
                <Spinner /> Analyzing...
              </>
            ) : (
              <>
                <SparklesIcon className="w-4 h-4" /> Analyze with AI
              </>
            )}
          </button>
        </div>
      )}

      {/* Entities */}
      {article.entities.length > 0 && (
        <div className="card">
          <div className="px-5 py-4 border-b border-ink-100">
            <h2 className="text-sm font-semibold text-ink-700 uppercase tracking-wider">
              Extracted Entities ({article.entities.length})
            </h2>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {article.entities.map((entity) => (
                <Link
                  key={entity.id}
                  to={`/entities/${entity.id}`}
                  className="flex items-center justify-between p-3 rounded-lg border border-ink-100 hover:border-ink-200 hover:bg-ink-50/50 transition-all"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <EntityBadge type={entity.type} name={entity.name} size="md" />
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <SentimentBar value={entity.sentiment} />
                    <span className="text-xs text-ink-400 tabular-nums w-8 text-right">
                      {(entity.relevance * 100).toFixed(0)}%
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="card p-6">
        <h2 className="text-sm font-semibold text-ink-500 uppercase tracking-wider mb-4">
          Full Article
        </h2>
        <div className="prose prose-sm max-w-none text-ink-700 leading-relaxed whitespace-pre-wrap">
          {article.content}
        </div>
      </div>
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────

function SentimentBar({ value }: { value: number }) {
  const normalized = Math.max(-1, Math.min(1, value));
  const pct = ((normalized + 1) / 2) * 100;
  const color = normalized > 0.2 ? "bg-sage-500" : normalized < -0.2 ? "bg-red-500" : "bg-ink-400";

  return (
    <div className="w-16 h-1.5 bg-ink-100 rounded-full overflow-hidden relative" title={`Sentiment: ${value.toFixed(2)}`}>
      <div
        className="absolute top-0 h-full w-1 rounded-full bg-ink-300"
        style={{ left: "50%" }}
      />
      <div
        className={`absolute top-0 h-full w-2 rounded-full ${color}`}
        style={{ left: `calc(${pct}% - 4px)` }}
      />
    </div>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

// ── Icons ──────────────────────────────────────────────────────────

function ChevronRight({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" />
      <path d="M19 17v4" />
      <path d="M3 5h4" />
      <path d="M17 19h4" />
    </svg>
  );
}
