import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import type { EntityDetail as EntityDetailType, EntityConnections } from "../types";
import { fetchEntity, fetchEntityConnections } from "../api/client";
import EntityGraph from "../components/EntityGraph";
import { EntityTypeBadge } from "../components/EntityBadge";
import ArticleCard, { ArticleCardSkeleton } from "../components/ArticleCard";

export default function EntityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [entity, setEntity] = useState<EntityDetailType | null>(null);
  const [connections, setConnections] = useState<EntityConnections | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const [entityData, connectionsData] = await Promise.all([
          fetchEntity(id!),
          fetchEntityConnections(id!),
        ]);

        if (cancelled) return;

        setEntity(entityData);
        setConnections(connectionsData);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load entity");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  function handleNodeClick(nodeId: string) {
    navigate(`/entities/${nodeId}`);
  }

  if (loading) {
    return (
      <div className="space-y-6 max-w-6xl">
        <div className="skeleton h-8 w-64" />
        <div className="skeleton h-4 w-32" />
        <div className="skeleton h-[400px] w-full rounded-xl" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <ArticleCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="text-center py-20">
        <p className="text-lg text-ink-600">{error || "Entity not found"}</p>
        <button onClick={() => navigate(-1)} className="btn-secondary mt-4">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-ink-400">
        <Link to="/entities" className="hover:text-accent-600 transition-colors">
          Entities
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-ink-600">{entity.name}</span>
      </nav>

      {/* Header */}
      <header className="flex items-start gap-4">
        <div>
          <h1 className="text-3xl font-serif font-bold text-ink-900">{entity.name}</h1>
          <div className="mt-2 flex items-center gap-3">
            <EntityTypeBadge type={entity.type} />
            <span className="text-sm text-ink-500">
              {entity.article_count} article{entity.article_count !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </header>

      {/* Connection graph */}
      {connections && connections.nodes.length > 0 && (
        <div className="card">
          <div className="px-5 py-4 border-b border-ink-100">
            <h2 className="text-base font-serif font-semibold text-ink-900">
              Entity Connections
            </h2>
            <p className="text-xs text-ink-400 mt-0.5">
              Relationships based on co-occurrence in articles. Click a node to navigate.
            </p>
          </div>
          <div className="h-[480px]">
            <EntityGraph connections={connections} onNodeClick={handleNodeClick} />
          </div>
          {/* Legend */}
          <div className="px-5 py-3 border-t border-ink-100 flex flex-wrap gap-4">
            {[
              { type: "person", color: "bg-accent-500" },
              { type: "company", color: "bg-rust-500" },
              { type: "location", color: "bg-sage-500" },
              { type: "topic", color: "bg-purple-500" },
              { type: "event", color: "bg-amber-500" },
            ].map(({ type, color }) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-ink-500">
                <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </div>
            ))}
          </div>
        </div>
      )}

      {connections && connections.nodes.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-sm text-ink-400">No connections found for this entity yet.</p>
        </div>
      )}

      {/* Related articles */}
      <div className="card">
        <div className="px-5 py-4 border-b border-ink-100">
          <h2 className="text-base font-serif font-semibold text-ink-900">
            Related Articles ({entity.articles?.length ?? 0})
          </h2>
        </div>
        <div className="divide-y divide-ink-100">
          {entity.articles && entity.articles.length > 0 ? (
            entity.articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))
          ) : (
            <div className="text-center py-12">
              <p className="text-sm text-ink-400">No related articles found.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ChevronRight({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}
