import type {
  PaginatedResponse,
  SingleResponse,
  ArticleListItem,
  ArticleDetail,
  EntityListItem,
  EntityDetail,
  EntityConnections,
  DashboardStats,
  TrendingEntity,
  ResearchTaskListItem,
  ResearchTaskDetail,
  Source,
} from "../types";

const BASE = "/api";

// ── Generic Fetch Helpers ──────────────────────────────────────────

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const res = await fetch(url.toString());
  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, body);
  }
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, text);
  }
  return res.json();
}

// ── Dashboard ──────────────────────────────────────────────────────

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await get<SingleResponse<DashboardStats>>("/dashboard/stats");
  return res.data;
}

export async function fetchTrends(): Promise<TrendingEntity[]> {
  const res = await get<SingleResponse<TrendingEntity[]>>("/dashboard/trends");
  return res.data;
}

// ── Articles ───────────────────────────────────────────────────────

export interface ArticleFilters {
  source_id?: string;
  topic?: string;
  search?: string;
  analyzed?: boolean;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}

export async function fetchArticles(filters: ArticleFilters = {}): Promise<PaginatedResponse<ArticleListItem>> {
  return get<PaginatedResponse<ArticleListItem>>("/articles", {
    source_id: filters.source_id,
    topic: filters.topic,
    search: filters.search,
    analyzed: filters.analyzed,
    from_date: filters.from_date,
    to_date: filters.to_date,
    limit: filters.limit ?? 20,
    offset: filters.offset ?? 0,
  });
}

export async function fetchArticle(id: string): Promise<ArticleDetail> {
  const res = await get<SingleResponse<ArticleDetail>>(`/articles/${id}`);
  return res.data;
}

export async function analyzeArticle(id: string): Promise<void> {
  await post(`/articles/${id}/analyze`);
}

// ── Entities ───────────────────────────────────────────────────────

export interface EntityFilters {
  type?: string;
  search?: string;
  min_articles?: number;
  limit?: number;
  offset?: number;
}

export async function fetchEntities(filters: EntityFilters = {}): Promise<PaginatedResponse<EntityListItem>> {
  return get<PaginatedResponse<EntityListItem>>("/entities", {
    type: filters.type,
    search: filters.search,
    min_articles: filters.min_articles,
    limit: filters.limit ?? 20,
    offset: filters.offset ?? 0,
  });
}

export async function fetchEntity(id: string): Promise<EntityDetail> {
  const res = await get<SingleResponse<EntityDetail>>(`/entities/${id}`);
  return res.data;
}

export async function fetchEntityConnections(id: string): Promise<EntityConnections> {
  const res = await get<SingleResponse<EntityConnections>>(`/entities/${id}/connections`);
  return res.data;
}

// ── Research ───────────────────────────────────────────────────────

export async function fetchResearchTasks(
  limit = 20,
  offset = 0,
): Promise<PaginatedResponse<ResearchTaskListItem>> {
  return get<PaginatedResponse<ResearchTaskListItem>>("/research", { limit, offset });
}

export async function fetchResearchTask(id: string): Promise<ResearchTaskDetail> {
  const res = await get<SingleResponse<ResearchTaskDetail>>(`/research/${id}`);
  return res.data;
}

export async function createResearchTask(query: string): Promise<ResearchTaskDetail> {
  const res = await post<SingleResponse<ResearchTaskDetail>>("/research", { query });
  return res.data;
}

export function streamResearch(id: string, onStep: (step: unknown) => void, onDone: () => void): () => void {
  const es = new EventSource(`${BASE}/research/${id}/stream`);

  es.addEventListener("step", (event) => {
    try {
      const data = JSON.parse((event as MessageEvent).data);
      onStep(data);
    } catch {
      // ignore parse errors
    }
  });

  es.addEventListener("complete", () => {
    onDone();
    es.close();
  });

  es.onerror = () => {
    onDone();
    es.close();
  };

  return () => es.close();
}

// ── Sources ────────────────────────────────────────────────────────

export async function fetchSources(): Promise<Source[]> {
  const res = await get<PaginatedResponse<Source>>("/sources");
  return res.data;
}

export async function createSource(data: { name: string; url: string; category?: string }): Promise<Source> {
  const res = await post<SingleResponse<Source>>("/sources", data);
  return res.data;
}
