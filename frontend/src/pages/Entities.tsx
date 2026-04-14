import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import type { EntityListItem, EntityType } from "../types";
import { fetchEntities, type EntityFilters } from "../api/client";
import { EntityTypeBadge } from "../components/EntityBadge";

const PAGE_SIZE = 20;

const entityTypes: { value: string; label: string }[] = [
  { value: "", label: "All Types" },
  { value: "person", label: "Person" },
  { value: "company", label: "Company" },
  { value: "location", label: "Location" },
  { value: "topic", label: "Topic" },
  { value: "event", label: "Event" },
];

export default function Entities() {
  const [entities, setEntities] = useState<EntityListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [searchDebounce, setSearchDebounce] = useState("");

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounce(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const loadEntities = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const filters: EntityFilters = {
        limit: PAGE_SIZE,
        offset,
        search: searchDebounce || undefined,
        type: typeFilter || undefined,
      };

      const result = await fetchEntities(filters);
      setEntities(result.data);
      setTotal(result.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load entities");
    } finally {
      setLoading(false);
    }
  }, [offset, searchDebounce, typeFilter]);

  useEffect(() => {
    setOffset(0);
  }, [searchDebounce, typeFilter]);

  useEffect(() => {
    loadEntities();
  }, [loadEntities]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-serif font-bold text-ink-900">Entities</h1>
        <p className="mt-1 text-sm text-ink-500">
          People, companies, locations, and topics extracted from news
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
                placeholder="Search entities..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-9"
              />
            </div>
          </div>
          <div className="w-40">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="input"
            >
              {entityTypes.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
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

      {/* Entity list */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="card p-4">
              <div className="skeleton h-5 w-2/3 mb-2" />
              <div className="skeleton h-4 w-1/3 mb-3" />
              <div className="skeleton h-3 w-1/4" />
            </div>
          ))}
        </div>
      ) : entities.length === 0 ? (
        <div className="card p-12 text-center">
          <EmptyIcon className="w-12 h-12 text-ink-300 mx-auto" />
          <p className="text-sm text-ink-500 mt-3">No entities found</p>
          <p className="text-xs text-ink-400 mt-1">
            {search || typeFilter
              ? "Try adjusting your filters"
              : "Entities will appear as articles are analyzed"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {entities.map((entity) => (
            <EntityCard key={entity.id} entity={entity} />
          ))}
        </div>
      )}

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

// ── Entity Card ────────────────────────────────────────────────────

function EntityCard({ entity }: { entity: EntityListItem }) {
  return (
    <Link to={`/entities/${entity.id}`} className="card-hover p-4 block group">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-ink-900 group-hover:text-accent-600 transition-colors truncate">
            {entity.name}
          </h3>
          <div className="mt-1.5">
            <EntityTypeBadge type={entity.type as EntityType} />
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          <p className="text-lg font-semibold text-ink-700 tabular-nums">
            {entity.article_count}
          </p>
          <p className="text-xs text-ink-400">articles</p>
        </div>
      </div>
    </Link>
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
      <circle cx="12" cy="12" r="10" />
      <path d="M8 12h8" />
    </svg>
  );
}
