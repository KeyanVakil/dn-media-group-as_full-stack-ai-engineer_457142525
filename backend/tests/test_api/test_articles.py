"""Tests for the articles API endpoints.

Uses httpx AsyncClient with mocked database session to test:
- GET /api/articles (paginated list, search filter)
- GET /api/articles/:id (article detail with summary and entities)
- 404 handling for missing articles
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestListArticles:
    """GET /api/articles"""

    @pytest.mark.asyncio
    async def test_returns_paginated_list(self, client, mock_session, sample_article):
        """Should return articles with pagination metadata."""
        # Mock count query result
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        # Mock articles query result
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_article]
        articles_result = MagicMock()
        articles_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, articles_result])

        response = await client.get("/api/articles")

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["total"] == 1
        assert body["meta"]["limit"] == 20
        assert body["meta"]["offset"] == 0
        assert len(body["data"]) == 1
        assert body["data"][0]["title"] == "Tech Giant Acquires AI Startup"

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client, mock_session):
        """Should return empty data when no articles exist."""
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        articles_result = MagicMock()
        articles_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, articles_result])

        response = await client.get("/api/articles")

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_search_filter(self, client, mock_session, sample_article):
        """Should accept search query parameter."""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_article]
        articles_result = MagicMock()
        articles_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, articles_result])

        response = await client.get("/api/articles", params={"search": "AI"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 1

    @pytest.mark.asyncio
    async def test_pagination_params(self, client, mock_session):
        """Should respect limit and offset parameters."""
        count_result = MagicMock()
        count_result.scalar.return_value = 50

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        articles_result = MagicMock()
        articles_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, articles_result])

        response = await client.get("/api/articles", params={"limit": 10, "offset": 20})

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["limit"] == 10
        assert body["meta"]["offset"] == 20

    @pytest.mark.asyncio
    async def test_analyzed_filter(self, client, mock_session, sample_article):
        """Should filter by analyzed status."""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_article]
        articles_result = MagicMock()
        articles_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, articles_result])

        response = await client.get("/api/articles", params={"analyzed": True})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_limit_validation_too_high(self, client, mock_session):
        """Limit above 100 should be rejected."""
        response = await client.get("/api/articles", params={"limit": 200})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_limit_validation_too_low(self, client, mock_session):
        """Limit below 1 should be rejected."""
        response = await client.get("/api/articles", params={"limit": 0})
        assert response.status_code == 422


class TestGetArticle:
    """GET /api/articles/:id"""

    @pytest.mark.asyncio
    async def test_returns_article_detail(
        self, client, mock_session, sample_article, sample_article_summary, sample_article_entity
    ):
        """Should return full article with summary and entities."""
        sample_article.summary = sample_article_summary
        sample_article.article_entities = [sample_article_entity]

        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = sample_article
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        response = await client.get(f"/api/articles/{sample_article.id}")

        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        assert data["title"] == "Tech Giant Acquires AI Startup"
        assert data["summary"]["summary"] == "A major tech company acquired an AI startup for $2B."
        assert len(data["summary"]["topics"]) == 2
        assert len(data["entities"]) == 1
        assert data["entities"][0]["name"] == "Google"

    @pytest.mark.asyncio
    async def test_returns_article_without_summary(self, client, mock_session, sample_article):
        """Article without analysis should have null summary."""
        sample_article.summary = None
        sample_article.article_entities = []

        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = sample_article
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        response = await client.get(f"/api/articles/{sample_article.id}")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["summary"] is None
        assert data["entities"] == []

    @pytest.mark.asyncio
    async def test_404_for_missing_article(self, client, mock_session):
        """Should return 404 when article is not found."""
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        fake_id = uuid.uuid4()
        response = await client.get(f"/api/articles/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Article not found"

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client, mock_session):
        """An invalid UUID path parameter should return 422."""
        response = await client.get("/api/articles/not-a-uuid")
        assert response.status_code == 422


class TestTriggerAnalysis:
    """POST /api/articles/:id/analyze"""

    @pytest.mark.asyncio
    async def test_triggers_analysis_returns_202(self, client, mock_session, sample_article):
        """Should return 202 and trigger background analysis."""
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = sample_article
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        # Mock the background task to avoid it connecting to a real database
        with patch("app.api.articles._analyze_in_background", new_callable=AsyncMock):
            response = await client.post(f"/api/articles/{sample_article.id}/analyze")

        assert response.status_code == 202
        body = response.json()
        assert body["data"]["message"] == "Analysis triggered"

    @pytest.mark.asyncio
    async def test_404_for_missing_article(self, client, mock_session):
        """Should return 404 if article does not exist."""
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        fake_id = uuid.uuid4()
        response = await client.post(f"/api/articles/{fake_id}/analyze")
        assert response.status_code == 404
