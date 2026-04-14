"""Shared fixtures for the NewsLens test suite.

Uses httpx.AsyncClient against the FastAPI app with dependency overrides
to inject a mock database session. Since the models use PostgreSQL-specific
column types (UUID, JSONB), we mock at the session level rather than
attempting to run SQLite in-memory.
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def mock_session() -> AsyncMock:
    """Create a mock AsyncSession for database operations."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest_asyncio.fixture
async def client(mock_session: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Create an httpx AsyncClient with the DB session overridden by a mock."""

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------

def make_uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def source_id() -> uuid.UUID:
    return make_uuid()


@pytest.fixture
def article_id() -> uuid.UUID:
    return make_uuid()


@pytest.fixture
def entity_id() -> uuid.UUID:
    return make_uuid()


@pytest.fixture
def sample_source(source_id):
    """Return a mock Source ORM object."""
    source = MagicMock()
    source.id = source_id
    source.name = "Reuters Business"
    source.url = "https://feeds.reuters.com/reuters/businessNews"
    source.category = "finance"
    source.active = True
    source.last_fetched_at = None
    source.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return source


@pytest.fixture
def sample_article(article_id, source_id, sample_source):
    """Return a mock Article ORM object with a related source."""
    article = MagicMock()
    article.id = article_id
    article.source_id = source_id
    article.source = sample_source
    article.external_url = "https://example.com/article/1"
    article.title = "Tech Giant Acquires AI Startup"
    article.content = "A major technology company announced today..."
    article.author = "Jane Doe"
    article.published_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    article.ingested_at = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    article.analyzed = True
    article.analyzed_at = datetime(2026, 4, 1, 12, 5, tzinfo=timezone.utc)
    article.summary = None
    article.article_entities = []
    return article


@pytest.fixture
def sample_article_summary(article_id):
    """Return a mock ArticleSummary ORM object."""
    summary = MagicMock()
    summary.id = make_uuid()
    summary.article_id = article_id
    summary.summary = "A major tech company acquired an AI startup for $2B."
    summary.topics = ["mergers & acquisitions", "artificial intelligence"]
    summary.key_facts = ["Acquisition valued at $2 billion", "Deal expected to close Q3"]
    summary.created_at = datetime(2026, 4, 1, 12, 5, tzinfo=timezone.utc)
    return summary


@pytest.fixture
def sample_entity(entity_id):
    """Return a mock Entity ORM object."""
    entity = MagicMock()
    entity.id = entity_id
    entity.name = "Google"
    entity.type = "company"
    entity.description = "Alphabet subsidiary"
    entity.article_count = 15
    entity.first_seen_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    entity.article_entities = []
    return entity


@pytest.fixture
def sample_article_entity(article_id, entity_id, sample_entity):
    """Return a mock ArticleEntity join object."""
    ae = MagicMock()
    ae.id = make_uuid()
    ae.article_id = article_id
    ae.entity_id = entity_id
    ae.entity = sample_entity
    ae.sentiment = 0.3
    ae.relevance = 0.9
    ae.context = "Google announced the acquisition..."
    return ae


@pytest.fixture
def sample_entity_relationship():
    """Return a mock EntityRelationship ORM object."""
    rel = MagicMock()
    rel.id = make_uuid()
    rel.entity_a_id = make_uuid()
    rel.entity_b_id = make_uuid()
    rel.relationship_type = "co-occurrence"
    rel.strength = 0.3
    rel.evidence_count = 3
    rel.last_seen_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    return rel


@pytest.fixture
def sample_research_task():
    """Return a mock ResearchTask ORM object."""
    task = MagicMock()
    task.id = make_uuid()
    task.query = "What is the impact of AI on financial markets?"
    task.status = "completed"
    task.result = {
        "briefing": "AI is transforming financial markets...",
        "key_findings": ["Automated trading increased 40%"],
        "evidence": [],
        "follow_up_questions": ["How does regulation affect AI trading?"],
    }
    task.created_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    task.completed_at = datetime(2026, 4, 1, 0, 5, tzinfo=timezone.utc)
    task.steps = []
    return task


@pytest.fixture
def sample_research_step(sample_research_task):
    """Return a mock ResearchStep ORM object."""
    step = MagicMock()
    step.id = make_uuid()
    step.task_id = sample_research_task.id
    step.step_number = 1
    step.action = "parse_query"
    step.input_data = {"query": sample_research_task.query}
    step.output_data = None
    step.created_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    return step


@pytest.fixture
def extraction_result():
    """Sample Claude extraction response used across entity tests."""
    return {
        "summary": "A major tech company acquired an AI startup for $2B.",
        "topics": ["mergers & acquisitions", "artificial intelligence"],
        "key_facts": ["Acquisition valued at $2 billion"],
        "entities": [
            {
                "name": "Google",
                "type": "company",
                "sentiment": 0.5,
                "relevance": 0.95,
                "context": "Google announced the acquisition...",
            },
            {
                "name": "DeepMind",
                "type": "company",
                "sentiment": 0.3,
                "relevance": 0.8,
                "context": "DeepMind, the AI startup...",
            },
            {
                "name": "Sundar Pichai",
                "type": "person",
                "sentiment": 0.2,
                "relevance": 0.6,
                "context": "CEO Sundar Pichai stated...",
            },
        ],
    }
