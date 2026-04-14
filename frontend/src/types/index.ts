// ── API Response Wrappers ──────────────────────────────────────────

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface SingleResponse<T> {
  data: T;
}

// ── Source ──────────────────────────────────────────────────────────

export interface Source {
  id: string;
  name: string;
  url: string;
  category?: string;
}

// ── Article ────────────────────────────────────────────────────────

export interface ArticleListItem {
  id: string;
  title: string;
  source: { id: string; name: string };
  published_at: string;
  analyzed: boolean;
  ingested_at: string;
}

export interface ArticleSummary {
  summary: string;
  topics: string[];
  key_facts: string[];
}

export interface ArticleEntity {
  id: string;
  name: string;
  type: EntityType;
  sentiment: number;
  relevance: number;
}

export interface ArticleDetail {
  id: string;
  source: Source;
  title: string;
  content: string;
  author: string | null;
  published_at: string;
  summary: ArticleSummary | null;
  entities: ArticleEntity[];
}

// ── Entity ─────────────────────────────────────────────────────────

export type EntityType = "person" | "company" | "location" | "topic" | "event";

export interface EntityListItem {
  id: string;
  name: string;
  type: EntityType;
  article_count: number;
}

export interface EntityDetail {
  id: string;
  name: string;
  type: EntityType;
  description: string | null;
  article_count: number;
  articles: ArticleListItem[];
}

export interface EntityConnectionNode {
  id: string;
  name: string;
  type: EntityType;
  article_count: number;
}

export interface EntityConnectionEdge {
  source: string;
  target: string;
  strength: number;
  evidence_count: number;
}

export interface EntityConnections {
  center: EntityConnectionNode;
  nodes: EntityConnectionNode[];
  edges: EntityConnectionEdge[];
}

// ── Dashboard ──────────────────────────────────────────────────────

export interface DashboardStats {
  total_articles: number;
  total_entities: number;
  total_sources: number;
  articles_analyzed: number;
  research_tasks_completed: number;
}

export interface TrendingEntity {
  entity: { id: string; name: string; type: EntityType };
  mention_count: number;
  sentiment_avg: number;
}

// ── Research ───────────────────────────────────────────────────────

export type ResearchStatus = "pending" | "running" | "completed" | "failed";

export interface ResearchTaskListItem {
  id: string;
  query: string;
  status: ResearchStatus;
  created_at: string;
}

export interface ResearchStep {
  step_number: number;
  action: string;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
}

export interface EvidenceItem {
  article_id: string;
  title: string;
  relevance: string;
}

export interface ResearchResult {
  briefing: string;
  key_findings: string[];
  evidence: EvidenceItem[];
  follow_up_questions: string[];
}

export interface ResearchTaskDetail {
  id: string;
  query: string;
  status: ResearchStatus;
  steps: ResearchStep[];
  result: ResearchResult | null;
  created_at: string;
}
