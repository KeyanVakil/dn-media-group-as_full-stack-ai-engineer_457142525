# NewsLens -- AI Editorial Intelligence Platform

An AI-powered editorial intelligence platform that ingests financial news from RSS feeds, extracts named entities using Claude, builds a relationship knowledge graph, and provides an AI research agent for investigative journalism.

Built as a demo project for the [Full-stack AI Engineer](https://www.finn.no/job/ad/457142525) position at DN Media Group AS.

---

## Skills Demonstrated

| Job Requirement | Where It's Demonstrated |
|-----------------|------------------------|
| **Python** | FastAPI backend: async REST API, Pydantic validation, SQLAlchemy 2.0 ORM, background task orchestration |
| **AI/LLM Integration** | Claude-powered entity extraction (structured tool output), multi-step research agent with tool use |
| **Full-stack Development** | React + TypeScript frontend with D3 graph visualization, Go concurrent ingester, PostgreSQL data modeling |
| **Systems Design** | Multi-service architecture: Go worker, Python API, React SPA, PostgreSQL, all orchestrated via Docker Compose |
| **Data Pipelines** | RSS ingestion -> AI analysis -> entity extraction -> relationship graph building -> research synthesis |
| **API Design** | RESTful API with OpenAPI docs, pagination, filtering, SSE streaming, consistent response format |
| **DevOps** | Docker multi-stage builds, health checks, service dependency ordering, GitHub Actions CI |

---

## Architecture

```
RSS Feeds ──► Go Ingester ──► PostgreSQL ◄── FastAPI Backend ──► Claude API
                                                    │
                                              React Frontend
                                            (Dashboard, Entities,
                                             Research Agent)
```

| Component | Language | Responsibility |
|-----------|----------|----------------|
| **Go Ingester** | Go 1.22 | Concurrent RSS feed fetching with goroutines, deduplication, scheduled polling |
| **FastAPI Backend** | Python 3.12 | REST API, AI-powered article analysis, entity extraction, research agent |
| **React Frontend** | TypeScript/React 18 | Editorial dashboard, entity explorer with D3 graph, research agent chat |
| **PostgreSQL** | SQL | Articles, entities, relationships, research tasks |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An Anthropic API key (for AI features)

### Run

```bash
# 1. Clone the repository
git clone <repo-url> && cd newslens

# 2. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Start everything
docker compose up --build
```

### Access

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API Base**: http://localhost:8000/api

Within ~1 minute, the system ingests real articles from public RSS feeds and begins AI analysis automatically.

> **Note**: The platform works without an API key -- articles are ingested and browsable, but AI analysis and the research agent require a valid `ANTHROPIC_API_KEY`.

---

## How to Run the Tests

### Backend (Python)

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Ingester (Go)

```bash
cd ingester
go test ./... -v
```

### Frontend (React)

```bash
cd frontend
npm install
npm test
```

---

## Tech Stack

| Technology | Role | Rationale |
|-----------|------|-----------|
| **Python 3.12 / FastAPI** | Backend API | Async-first framework with auto-generated OpenAPI docs and Pydantic validation |
| **Go 1.22** | RSS Ingester | Goroutines provide natural concurrency for parallel feed fetching |
| **React 18 / TypeScript** | Frontend | Industry-standard for interactive dashboards; TypeScript for type safety |
| **PostgreSQL 16** | Database | Robust relational DB with JSONB for flexible AI outputs |
| **SQLAlchemy 2.0** | ORM | Async support with type-safe models |
| **Anthropic Claude** | AI/NLP | Entity extraction via structured tool output; multi-step research agent via tool use |
| **D3.js** | Visualization | Force-directed graph for entity relationship exploration |
| **Tailwind CSS** | Styling | Utility-first CSS for rapid, consistent UI development |
| **Docker Compose** | Deployment | Complete local stack with one command |

---

## Key Features

### 1. Multi-Source Article Ingestion
The Go ingester fetches RSS feeds concurrently using a goroutine pool with configurable concurrency. Articles are deduplicated by URL and stored in PostgreSQL.

### 2. AI-Powered Article Analysis
Claude analyzes each article to extract named entities (people, companies, locations), generate summaries, identify topics, and extract key facts. Uses structured tool output for consistent JSON formatting.

### 3. Entity Relationship Graph
Entities that co-occur in articles form relationships. The strength of each relationship increases with the number of co-occurring articles, building a knowledge graph over time.

### 4. AI Research Agent
A multi-step investigation agent that uses Claude with tool use to search articles, map entities, discover connections, and synthesize structured briefings. Each step is recorded for full transparency.

### 5. Editorial Dashboard
Interactive React frontend with article browsing, entity exploration (including D3 force-directed graph visualization), and a research agent interface with real-time SSE streaming.

---

## Project Structure

```
newslens/
├── backend/          Python FastAPI backend
│   ├── app/
│   │   ├── api/      REST API routes
│   │   ├── models/   SQLAlchemy models
│   │   ├── schemas/  Pydantic schemas
│   │   └── services/ Business logic (analyzer, entity extractor, graph builder, research agent)
│   └── tests/        pytest unit and integration tests
├── ingester/         Go RSS feed ingester
│   ├── cmd/          Entry point
│   └── internal/     Config, fetcher, parser, store
├── frontend/         React TypeScript SPA
│   └── src/
│       ├── api/      API client
│       ├── components/  Reusable UI components
│       ├── pages/    Page-level components
│       └── types/    TypeScript interfaces
├── db/               Database init scripts
└── docker-compose.yml
```
