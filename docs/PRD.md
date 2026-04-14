# PRD: NewsLens -- AI Editorial Intelligence Platform

## 1. Project Overview

**NewsLens** is an AI-powered editorial intelligence platform built for financial news organizations. It ingests articles from RSS feeds, uses AI to extract named entities (companies, people, markets, events), tracks relationships between entities across articles over time, and provides an AI research agent that journalists can use to investigate topics and discover hidden connections between stories.

### Why this is relevant to DN Media Group

DN Media Group publishes Dagens Naeringsliv (Norway's leading financial daily) along with specialist titles covering shipping, seafood, and energy. The newly established Editorial AI team's mandate is to build tools that support investigative journalism and create AI-driven content experiences. NewsLens demonstrates exactly this: AI applied to the editorial workflow, helping journalists discover stories that would otherwise require days of manual cross-referencing.

### The problem it solves

Financial journalists track hundreds of companies, executives, and market events across thousands of articles. Connections between entities -- a board member who sits on two companies involved in a merger, or a regulatory change affecting multiple sectors -- are often invisible until a journalist manually connects the dots. NewsLens automates entity extraction and relationship discovery, then provides an AI research agent that can investigate topics on demand, surfacing connections and generating structured briefings.

---

## 2. Technical Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           Docker Compose Network          │
                    │                                           │
 RSS Feeds ───────► │  ┌──────────┐      ┌──────────────────┐  │
 (Reuters, BBC,     │  │   Go     │      │  Python FastAPI   │  │
  financial news)   │  │ Ingester │─────►│     Backend       │  │
                    │  │ (worker) │      │                    │  │
                    │  └────┬─────┘      │  - REST API        │  │
                    │       │            │  - AI Analysis      │  │
                    │       │            │  - Entity Extraction│  │
                    │       ▼            │  - Research Agent   │  │
                    │  ┌──────────┐      │                    │  │
                    │  │PostgreSQL│◄─────│                    │  │
                    │  │          │      └────────┬───────────┘  │
                    │  └──────────┘               │              │
                    │                             │              │
                    │                    ┌────────▼───────────┐  │
                    │                    │   React Frontend    │  │
                    │                    │   (TypeScript)      │  │
                    │                    │                     │  │  ◄──── Browser
                    │                    │  - Dashboard        │  │
                    │                    │  - Entity Explorer  │  │
                    │                    │  - Research Agent UI│  │
                    │                    └─────────────────────┘  │
                    │                                             │
                    │              Claude API ◄───────────────────│
                    └─────────────────────────────────────────────┘
```

### Key components

| Component | Language | Responsibility |
|-----------|----------|----------------|
| **Go Ingester** | Go | Fetches RSS feeds concurrently, parses articles, deduplicates, writes to PostgreSQL. Runs on startup and on a configurable interval. |
| **Python Backend** | Python (FastAPI) | REST API, AI-powered article analysis, entity extraction, relationship graph building, research agent orchestration. |
| **React Frontend** | TypeScript (React) | Editorial dashboard with article browsing, entity explorer, relationship visualization, and research agent chat interface. |
| **PostgreSQL** | -- | Persistent storage for articles, entities, relationships, and research tasks. |

### Data flow

1. **Ingestion**: Go worker fetches RSS feeds concurrently, parses article metadata and content, deduplicates by URL, stores raw articles in PostgreSQL.
2. **Analysis**: Backend picks up unanalyzed articles, sends content to Claude for entity extraction, summarization, and topic classification. Results stored back in PostgreSQL.
3. **Graph Building**: After entity extraction, the backend identifies relationships between entities that co-occur in articles and updates the relationship graph.
4. **Research**: When a journalist submits a research query, the AI agent searches the article database, finds relevant entities, discovers connections, and generates a structured briefing. Each step is recorded for transparency.
5. **Presentation**: The React frontend queries the API to display articles, entities, relationship graphs, and research results.

---

## 3. Tech Stack

| Technology | Role | Rationale |
|-----------|------|-----------|
| **Python 3.12** | Backend API, AI services | Primary language required by the role. FastAPI for async performance. |
| **FastAPI** | Web framework | Async-first, auto-generated OpenAPI docs, Pydantic validation. |
| **Go 1.22** | RSS feed ingester | Demonstrates systems-language interest (bonus skill). Go's goroutines are a natural fit for concurrent HTTP feed fetching. |
| **React 18 + TypeScript** | Frontend | Full-stack role requires frontend capability. React is the industry standard for interactive dashboards. |
| **PostgreSQL 16** | Primary database | Robust relational database with JSONB support for flexible AI outputs. Demonstrates data modeling skills. |
| **SQLAlchemy 2.0** | Python ORM | Async support, type-safe models, Alembic migrations. |
| **Anthropic SDK (Claude)** | AI/NLP | Entity extraction, summarization, research agent reasoning. Tool-use for the multi-step research agent. |
| **Docker Compose** | Local deployment | Everything runs with `docker compose up`. No cloud accounts needed. |

---

## 4. Features & Acceptance Criteria

### Feature 1: Multi-Source Article Ingestion (Go)

The Go ingester fetches articles from configurable RSS feed sources concurrently and stores them in PostgreSQL.

**Acceptance Criteria:**
- Ingester reads a list of RSS feed sources from the database (seeded on first run).
- Fetches all feeds concurrently using goroutines with a configurable concurrency limit.
- Parses RSS/Atom feed formats and extracts title, URL, published date, and content/description.
- Deduplicates articles by URL -- skips articles already in the database.
- Runs once on container startup, then repeats on a configurable interval (default: 15 minutes).
- Logs ingestion stats (feeds fetched, articles added, duplicates skipped) to stdout.
- Handles feed fetch failures gracefully (logs error, continues with other feeds).

### Feature 2: AI-Powered Article Analysis

The backend analyzes ingested articles using Claude to extract structured intelligence.

**Acceptance Criteria:**
- A background task picks up articles where `analyzed = false` and processes them.
- For each article, Claude extracts:
  - **Named entities**: people, companies, locations, topics, events -- each with a type label.
  - **Summary**: 2-3 sentence summary of the article.
  - **Topics**: list of topic tags (e.g., "mergers & acquisitions", "oil & gas", "earnings").
  - **Key facts**: structured list of factual claims in the article.
- Entity extraction uses Claude's structured output (tool use) to ensure consistent JSON format.
- Extracted entities are matched against existing entities in the database (fuzzy name matching) to avoid duplicates.
- Each article-entity association includes a sentiment score (-1 to 1) and a relevance score (0 to 1).
- Analysis results are stored in the database; article is marked as analyzed.
- API endpoint `POST /api/articles/{id}/analyze` allows manually triggering re-analysis.

### Feature 3: Entity Relationship Graph

The system tracks relationships between entities that co-occur across articles, building a knowledge graph over time.

**Acceptance Criteria:**
- After article analysis, the system identifies entity pairs that co-occur in the same article.
- Co-occurrence creates or strengthens a relationship between the two entities.
- Relationship strength increases with the number of co-occurring articles.
- Entity detail pages show related entities ranked by relationship strength.
- API endpoint `GET /api/entities/{id}/connections` returns the entity's relationship subgraph (entities + edges) up to 2 hops.
- Trending entities (most mentioned in recent articles) are surfaced via `GET /api/dashboard/trends`.

### Feature 4: AI Research Agent

An AI-powered research agent that investigates topics by searching the article database, finding entity connections, and generating structured briefings.

**Acceptance Criteria:**
- Journalist submits a natural language research query (e.g., "What connections exist between Equinor and recent regulatory changes in the North Sea?").
- The agent executes a multi-step investigation using Claude with tool use:
  1. **Parse query**: Identify key entities and topics to investigate.
  2. **Search articles**: Find relevant articles in the database.
  3. **Map entities**: Identify all entities connected to the query.
  4. **Discover connections**: Trace relationship paths between entities.
  5. **Synthesize**: Generate a structured briefing with findings, supporting evidence (article citations), and suggested follow-up questions.
- Each agent step is recorded as a `research_step` in the database, making the reasoning process transparent and auditable.
- The research task status is queryable via `GET /api/research/{id}` with real-time step updates.
- The API streams agent progress via Server-Sent Events (`GET /api/research/{id}/stream`).
- The frontend displays the agent's step-by-step progress and final briefing.

### Feature 5: Editorial Dashboard (React)

An interactive web dashboard for browsing articles, exploring entities, and using the research agent.

**Acceptance Criteria:**
- **Dashboard page**: Shows platform stats (article count, entity count, source count), trending entities, and recent articles.
- **Articles page**: Paginated list of articles with search and filter by source, date range, and topic. Article detail view shows summary, extracted entities (highlighted), and key facts.
- **Entities page**: Searchable list of entities with type filter (person, company, location, topic, event). Entity detail view shows related articles, connected entities, and a relationship visualization (simple graph rendered with D3 or similar).
- **Research page**: Interface to submit research queries, view active/completed research tasks, and read research briefings. Shows the agent's step-by-step reasoning alongside the final result.
- Responsive layout that works on desktop screens (1024px+).
- Loading states and error handling for all API interactions.

### Feature 6: REST API

A clean, documented REST API that powers the frontend and could be consumed by other editorial tools.

**Acceptance Criteria:**
- All endpoints follow RESTful conventions with consistent JSON response format.
- Paginated list endpoints with `limit` and `offset` query parameters.
- Search/filter support on articles (by source, date range, topic, full-text) and entities (by name, type).
- Auto-generated OpenAPI documentation available at `/docs`.
- Proper HTTP status codes (201 for creation, 404 for not found, 422 for validation errors).
- Response times under 200ms for list/detail endpoints (excluding AI operations).

---

## 5. Data Models

### Entity Relationship Diagram

```
sources 1──────M articles 1──────M article_entities M──────1 entities
                    │                                        │
                    │                                        │
                    1                                        M
                    │                                        │
              article_summaries                     entity_relationships
                                                    (self-referencing M:M)

research_tasks 1──────M research_steps
```

### Schema

#### `sources`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| name | VARCHAR(255) | NOT NULL | Human-readable source name |
| url | VARCHAR(2048) | NOT NULL, UNIQUE | RSS feed URL |
| category | VARCHAR(100) | NOT NULL | finance, shipping, energy, general |
| active | BOOLEAN | DEFAULT true | Whether to fetch this source |
| last_fetched_at | TIMESTAMPTZ | NULLABLE | Last successful fetch |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

#### `articles`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| source_id | UUID | FK -> sources, NOT NULL | |
| external_url | VARCHAR(2048) | NOT NULL, UNIQUE | Dedupe key |
| title | VARCHAR(1000) | NOT NULL | |
| content | TEXT | NOT NULL | Full article text or description |
| author | VARCHAR(500) | NULLABLE | |
| published_at | TIMESTAMPTZ | NULLABLE | From feed |
| ingested_at | TIMESTAMPTZ | DEFAULT now() | |
| analyzed | BOOLEAN | DEFAULT false | |
| analyzed_at | TIMESTAMPTZ | NULLABLE | |

#### `article_summaries`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| article_id | UUID | FK -> articles, UNIQUE | One summary per article |
| summary | TEXT | NOT NULL | AI-generated 2-3 sentence summary |
| topics | JSONB | DEFAULT '[]' | List of topic strings |
| key_facts | JSONB | DEFAULT '[]' | List of factual claims |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

#### `entities`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| name | VARCHAR(500) | NOT NULL | Canonical name |
| type | VARCHAR(50) | NOT NULL | person, company, location, topic, event |
| description | TEXT | NULLABLE | AI-generated description |
| first_seen_at | TIMESTAMPTZ | DEFAULT now() | |
| article_count | INTEGER | DEFAULT 0 | Denormalized count |

Unique constraint on `(name, type)`.

#### `article_entities`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| article_id | UUID | FK -> articles, NOT NULL | |
| entity_id | UUID | FK -> entities, NOT NULL | |
| sentiment | FLOAT | DEFAULT 0.0 | -1.0 (negative) to 1.0 (positive) |
| relevance | FLOAT | DEFAULT 0.5 | 0.0 to 1.0 |
| context | TEXT | NULLABLE | Text snippet where entity appears |

Unique constraint on `(article_id, entity_id)`.

#### `entity_relationships`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| entity_a_id | UUID | FK -> entities, NOT NULL | |
| entity_b_id | UUID | FK -> entities, NOT NULL | |
| relationship_type | VARCHAR(100) | DEFAULT 'co-occurrence' | |
| strength | FLOAT | DEFAULT 0.0 | 0.0 to 1.0, based on co-occurrence frequency |
| evidence_count | INTEGER | DEFAULT 1 | Number of articles where both appear |
| last_seen_at | TIMESTAMPTZ | DEFAULT now() | |

Unique constraint on `(entity_a_id, entity_b_id)` with `entity_a_id < entity_b_id` to avoid duplicate pairs.

#### `research_tasks`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| query | TEXT | NOT NULL | Natural language research question |
| status | VARCHAR(20) | DEFAULT 'pending' | pending, running, completed, failed |
| result | JSONB | NULLABLE | Structured findings from the agent |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| completed_at | TIMESTAMPTZ | NULLABLE | |

#### `research_steps`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | |
| task_id | UUID | FK -> research_tasks, NOT NULL | |
| step_number | INTEGER | NOT NULL | Ordered step index |
| action | VARCHAR(100) | NOT NULL | parse_query, search_articles, map_entities, discover_connections, synthesize |
| input_data | JSONB | NULLABLE | What the agent received |
| output_data | JSONB | NULLABLE | What the agent produced |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

---

## 6. API Design

Base URL: `http://localhost:8000/api`

All responses follow the format:
```json
{
  "data": { ... },
  "meta": { "total": 100, "limit": 20, "offset": 0 }
}
```

For single resources, `data` is an object. For lists, `data` is an array and `meta` contains pagination info.

### Sources

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sources` | List all RSS sources |
| POST | `/sources` | Add a new RSS source |
| PATCH | `/sources/{id}` | Update source (e.g., toggle active) |
| DELETE | `/sources/{id}` | Remove a source |

**POST /sources**
```json
// Request
{ "name": "Reuters Business", "url": "https://...", "category": "finance" }

// Response 201
{ "data": { "id": "uuid", "name": "Reuters Business", "url": "...", "category": "finance", "active": true, "last_fetched_at": null, "created_at": "..." } }
```

### Articles

| Method | Path | Description |
|--------|------|-------------|
| GET | `/articles` | List articles (paginated, filterable) |
| GET | `/articles/{id}` | Get article with summary and entities |
| POST | `/articles/{id}/analyze` | Trigger AI analysis for an article |

**GET /articles** query parameters:
- `source_id` (UUID) -- filter by source
- `topic` (string) -- filter by topic tag
- `search` (string) -- full-text search in title and content
- `analyzed` (boolean) -- filter by analysis status
- `from_date`, `to_date` (ISO date) -- filter by published date
- `limit` (int, default 20, max 100)
- `offset` (int, default 0)

**GET /articles/{id}**
```json
{
  "data": {
    "id": "uuid",
    "source": { "id": "uuid", "name": "Reuters Business" },
    "title": "Equinor announces North Sea expansion",
    "content": "...",
    "published_at": "2026-04-10T08:00:00Z",
    "summary": {
      "summary": "Equinor has announced plans to expand operations...",
      "topics": ["oil & gas", "North Sea", "energy investment"],
      "key_facts": ["Equinor plans $2B investment", "Expected completion 2028"]
    },
    "entities": [
      { "id": "uuid", "name": "Equinor", "type": "company", "sentiment": 0.6, "relevance": 0.95 },
      { "id": "uuid", "name": "North Sea", "type": "location", "sentiment": 0.0, "relevance": 0.8 }
    ]
  }
}
```

### Entities

| Method | Path | Description |
|--------|------|-------------|
| GET | `/entities` | List entities (paginated, filterable) |
| GET | `/entities/{id}` | Get entity with article count and description |
| GET | `/entities/{id}/connections` | Get relationship subgraph |

**GET /entities** query parameters:
- `type` (string) -- person, company, location, topic, event
- `search` (string) -- search by name
- `min_articles` (int) -- minimum article count
- `limit`, `offset`

**GET /entities/{id}/connections**
```json
{
  "data": {
    "center": { "id": "uuid", "name": "Equinor", "type": "company" },
    "nodes": [
      { "id": "uuid", "name": "Anders Opedal", "type": "person", "article_count": 15 },
      { "id": "uuid", "name": "North Sea", "type": "location", "article_count": 42 }
    ],
    "edges": [
      { "source": "uuid-equinor", "target": "uuid-opedal", "strength": 0.85, "evidence_count": 12 },
      { "source": "uuid-equinor", "target": "uuid-north-sea", "strength": 0.72, "evidence_count": 8 }
    ]
  }
}
```

### Research

| Method | Path | Description |
|--------|------|-------------|
| POST | `/research` | Submit a research query |
| GET | `/research` | List research tasks |
| GET | `/research/{id}` | Get task status, steps, and result |
| GET | `/research/{id}/stream` | SSE stream of agent progress |

**POST /research**
```json
// Request
{ "query": "What connections exist between Equinor and recent regulatory changes?" }

// Response 201
{ "data": { "id": "uuid", "query": "...", "status": "pending", "created_at": "..." } }
```

**GET /research/{id}**
```json
{
  "data": {
    "id": "uuid",
    "query": "What connections exist between Equinor and recent regulatory changes?",
    "status": "completed",
    "steps": [
      { "step_number": 1, "action": "parse_query", "output_data": { "entities": ["Equinor"], "topics": ["regulatory changes"] } },
      { "step_number": 2, "action": "search_articles", "output_data": { "article_count": 14 } },
      { "step_number": 3, "action": "map_entities", "output_data": { "entity_count": 8 } },
      { "step_number": 4, "action": "discover_connections", "output_data": { "connections_found": 5 } },
      { "step_number": 5, "action": "synthesize", "output_data": {} }
    ],
    "result": {
      "briefing": "Analysis of 14 articles reveals...",
      "key_findings": [ "..." ],
      "evidence": [ { "article_id": "uuid", "title": "...", "relevance": "..." } ],
      "follow_up_questions": [ "..." ]
    },
    "created_at": "...",
    "completed_at": "..."
  }
}
```

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/stats` | Platform statistics |
| GET | `/dashboard/trends` | Trending entities (last 7 days) |

**GET /dashboard/stats**
```json
{
  "data": {
    "total_articles": 1247,
    "total_entities": 892,
    "total_sources": 8,
    "articles_analyzed": 1183,
    "research_tasks_completed": 15
  }
}
```

**GET /dashboard/trends**
```json
{
  "data": [
    { "entity": { "id": "uuid", "name": "Equinor", "type": "company" }, "mention_count": 23, "sentiment_avg": 0.3 },
    { "entity": { "id": "uuid", "name": "ECB", "type": "company" }, "mention_count": 18, "sentiment_avg": -0.1 }
  ]
}
```

---

## 7. Testing Strategy

### Unit Tests (Python -- pytest)

**What to cover:**
- **Entity extraction parsing**: Given known Claude responses, verify entities are correctly parsed, deduplicated, and stored.
- **Relationship graph logic**: Verify co-occurrence detection, strength calculation, and subgraph queries.
- **Research agent step logic**: Test each agent step in isolation with mocked Claude responses -- query parsing, article search, entity mapping, connection discovery, synthesis.
- **API request validation**: Verify Pydantic schemas reject invalid input (bad UUIDs, out-of-range values, missing required fields).
- **Database model constraints**: Verify unique constraints, foreign key relationships, and default values.

**Approach:** Use pytest with `pytest-asyncio` for async tests. Mock the Anthropic SDK at the service boundary to test AI-dependent code deterministically. Use an in-memory SQLite database (or test PostgreSQL via testcontainers) for model tests.

### Integration Tests (Python -- pytest)

**What to cover:**
- **Full analysis pipeline**: Ingest a test article -> analyze -> verify entities and summary are created in the database.
- **Research agent end-to-end**: Submit a research query -> verify all steps execute -> verify result is structured correctly.
- **API endpoint integration**: Test endpoints against a real database to verify queries, filters, pagination, and response format.

**Approach:** Use `httpx.AsyncClient` with FastAPI's `TestClient`. Spin up a test PostgreSQL database via Docker (or use the same `docker-compose` with a test profile). Seed with known test data.

### Go Ingester Tests

**What to cover:**
- **RSS/Atom parsing**: Verify correct extraction of title, URL, date, content from sample feeds.
- **Deduplication**: Verify articles with duplicate URLs are skipped.
- **Concurrent fetching**: Verify goroutine pool respects concurrency limits and handles fetch failures.

**Approach:** Go standard `testing` package. Use `httptest` to serve sample RSS feeds locally.

### Frontend Tests

**What to cover:**
- **Component rendering**: Key components render without errors with mock data.
- **API integration**: Verify API client functions construct correct requests.

**Approach:** Vitest with React Testing Library for component tests.

---

## 8. Infrastructure & Deployment

Everything runs locally with `docker compose up`. The only external dependency is a Claude API key passed as an environment variable.

### docker-compose.yml services

| Service | Image/Build | Ports | Dependencies |
|---------|-------------|-------|--------------|
| **db** | postgres:16-alpine | 5432 | -- |
| **backend** | ./backend (Dockerfile) | 8000 | db |
| **ingester** | ./ingester (Dockerfile) | -- | db |
| **frontend** | ./frontend (Dockerfile) | 3000 | backend |

### Environment variables

```bash
# .env (only file the user needs to create)
ANTHROPIC_API_KEY=sk-ant-...
```

All other configuration has sensible defaults:
- `DATABASE_URL=postgresql+asyncpg://newslens:newslens@db:5432/newslens`
- `INGESTER_INTERVAL=900` (seconds, 15 minutes)
- `INGESTER_CONCURRENCY=10`
- `ANALYSIS_BATCH_SIZE=5`

### Startup sequence

1. `db` starts, runs init script to create database and seed default RSS sources.
2. `backend` starts, runs Alembic migrations on startup, begins background analysis task.
3. `ingester` starts, fetches all active feeds, then sleeps for the configured interval.
4. `frontend` starts, serves the React app via nginx, proxies `/api` to the backend.

Within ~1 minute of `docker compose up`, the system has real articles ingested from public RSS feeds and begins AI analysis automatically.

### Database initialization

A SQL init script (`db/init.sql`) seeds the default RSS sources:
- Reuters Business News
- BBC Business
- Financial Times (public feed)
- E24 (Norwegian financial news)
- The Guardian Business

---

## 9. Project Structure

```
newslens/
├── docs/
│   └── PRD.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, startup events, CORS
│   │   ├── config.py                  # Settings via pydantic-settings
│   │   ├── database.py                # Async SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── source.py              # Source model
│   │   │   ├── article.py             # Article + ArticleSummary models
│   │   │   ├── entity.py              # Entity + ArticleEntity + EntityRelationship
│   │   │   └── research.py            # ResearchTask + ResearchStep models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── source.py              # Pydantic request/response schemas
│   │   │   ├── article.py
│   │   │   ├── entity.py
│   │   │   └── research.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── sources.py             # /api/sources endpoints
│   │   │   ├── articles.py            # /api/articles endpoints
│   │   │   ├── entities.py            # /api/entities endpoints
│   │   │   ├── research.py            # /api/research endpoints
│   │   │   └── dashboard.py           # /api/dashboard endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── analyzer.py            # Article analysis orchestration
│   │       ├── entity_extractor.py    # Claude-powered entity extraction
│   │       ├── graph_builder.py       # Co-occurrence and relationship logic
│   │       └── research_agent.py      # Multi-step AI research agent
│   ├── tests/
│   │   ├── conftest.py                # Fixtures: test DB, client, mock Claude
│   │   ├── test_api/
│   │   │   ├── test_articles.py
│   │   │   ├── test_entities.py
│   │   │   └── test_research.py
│   │   └── test_services/
│   │       ├── test_analyzer.py
│   │       ├── test_entity_extractor.py
│   │       ├── test_graph_builder.py
│   │       └── test_research_agent.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── ingester/
│   ├── cmd/
│   │   └── ingester/
│   │       └── main.go                # Entry point, CLI flags, run loop
│   ├── internal/
│   │   ├── config/
│   │   │   └── config.go              # Configuration from env vars
│   │   ├── fetcher/
│   │   │   └── fetcher.go             # Concurrent HTTP feed fetcher
│   │   ├── parser/
│   │   │   └── parser.go              # RSS/Atom XML parsing
│   │   └── store/
│   │       └── store.go               # PostgreSQL insert with dedup
│   ├── internal/fetcher/
│   │   └── fetcher_test.go
│   ├── internal/parser/
│   │   └── parser_test.go
│   ├── Dockerfile
│   ├── go.mod
│   └── go.sum
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── main.tsx                   # App entry point
│   │   ├── App.tsx                    # Router setup
│   │   ├── api/
│   │   │   └── client.ts             # API client (fetch wrapper)
│   │   ├── components/
│   │   │   ├── Layout.tsx             # Shell: nav sidebar + content area
│   │   │   ├── ArticleCard.tsx
│   │   │   ├── EntityBadge.tsx
│   │   │   ├── EntityGraph.tsx        # D3 force-directed graph
│   │   │   ├── ResearchChat.tsx       # Research agent interaction
│   │   │   ├── TrendsList.tsx
│   │   │   └── StatsCards.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Articles.tsx
│   │   │   ├── ArticleDetail.tsx
│   │   │   ├── Entities.tsx
│   │   │   ├── EntityDetail.tsx
│   │   │   └── Research.tsx
│   │   └── types/
│   │       └── index.ts              # TypeScript interfaces matching API
│   ├── nginx.conf                     # Serves static files, proxies /api
│   ├── Dockerfile                     # Multi-stage: build + nginx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── db/
│   └── init.sql                       # Create database, seed RSS sources
├── docker-compose.yml
├── .env.example
└── README.md
```

### Module responsibilities

**backend/app/services/entity_extractor.py** -- The core AI integration point. Sends article text to Claude with a structured tool definition that forces output as a list of entities with type, sentiment, relevance, and context. Handles entity deduplication by fuzzy-matching against existing entities in the database.

**backend/app/services/research_agent.py** -- Implements the multi-step research agent using Claude's tool-use capability. Defines tools the agent can call: `search_articles(query, filters)`, `get_entity(name)`, `get_connections(entity_id)`, `get_article_detail(id)`. The agent decides which tools to call at each step, and the orchestrator executes them against the database, feeding results back to Claude until the agent calls `synthesize(briefing)` to produce the final output.

**backend/app/services/graph_builder.py** -- After entity extraction, this service processes all entity pairs in an article, creates or updates relationship records, and recalculates relationship strength as `min(1.0, evidence_count / 10)` (normalized so 10+ co-occurrences = maximum strength).

**ingester/internal/fetcher/fetcher.go** -- Manages a pool of goroutines that fetch RSS feeds concurrently. Uses a semaphore pattern (`chan struct{}`) to limit concurrency. Each goroutine fetches one feed, parses it, and sends parsed articles to a results channel.
