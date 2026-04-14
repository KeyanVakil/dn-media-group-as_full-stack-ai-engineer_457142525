"""Tests for the article analysis orchestrator.

Covers analyze_article with mocked sub-services (entity_extractor, graph_builder)
and error handling when Claude API fails.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.analyzer import analyze_article, analyze_pending_batch


class TestAnalyzeArticle:
    """Test suite for analyze_article."""

    def _make_article(self) -> MagicMock:
        article = MagicMock()
        article.id = uuid.uuid4()
        article.title = "Oil Prices Surge Amid Middle East Tensions"
        article.content = "Crude oil prices rose sharply today..."
        article.analyzed = False
        article.analyzed_at = None
        return article

    @pytest.mark.asyncio
    async def test_successful_analysis(self, mock_session):
        """Full success path: extract, summarize, store entities, build graph."""
        article = self._make_article()

        extraction = {
            "summary": "Oil prices increased due to geopolitical tensions.",
            "topics": ["oil & gas", "geopolitics"],
            "key_facts": ["Brent crude up 5%"],
            "entities": [
                {
                    "name": "OPEC",
                    "type": "company",
                    "sentiment": -0.2,
                    "relevance": 0.9,
                    "context": "OPEC members discussed...",
                }
            ],
        }

        ae_mock = MagicMock()
        ae_mock.entity_id = uuid.uuid4()

        with (
            patch(
                "app.services.analyzer.extract_entities",
                new_callable=AsyncMock,
                return_value=extraction,
            ) as mock_extract,
            patch(
                "app.services.analyzer.store_article_entities",
                new_callable=AsyncMock,
                return_value=[ae_mock],
            ) as mock_store,
            patch(
                "app.services.analyzer.update_relationships",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_graph,
        ):
            result = await analyze_article(mock_session, article)

        assert result is True
        mock_extract.assert_awaited_once_with(article.title, article.content)
        mock_store.assert_awaited_once()
        mock_graph.assert_awaited_once_with(mock_session, [ae_mock.entity_id])

        # Article should be marked as analyzed
        assert article.analyzed is True
        assert article.analyzed_at is not None
        mock_session.commit.assert_awaited_once()
        mock_session.add.assert_called_once()  # ArticleSummary

    @pytest.mark.asyncio
    async def test_summary_is_created_from_extraction(self, mock_session):
        """Verify that an ArticleSummary is created with extraction data."""
        article = self._make_article()

        extraction = {
            "summary": "Test summary text.",
            "topics": ["tech"],
            "key_facts": ["Fact A", "Fact B"],
            "entities": [],
        }

        with (
            patch(
                "app.services.analyzer.extract_entities",
                new_callable=AsyncMock,
                return_value=extraction,
            ),
            patch(
                "app.services.analyzer.store_article_entities",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.analyzer.update_relationships",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            await analyze_article(mock_session, article)

        added_summary = mock_session.add.call_args[0][0]
        assert added_summary.article_id == article.id
        assert added_summary.summary == "Test summary text."
        assert added_summary.topics == ["tech"]
        assert added_summary.key_facts == ["Fact A", "Fact B"]

    @pytest.mark.asyncio
    async def test_handles_extraction_failure(self, mock_session):
        """If Claude API fails, analyze_article returns False and rolls back."""
        article = self._make_article()

        with patch(
            "app.services.analyzer.extract_entities",
            new_callable=AsyncMock,
            side_effect=Exception("API rate limit exceeded"),
        ):
            result = await analyze_article(mock_session, article)

        assert result is False
        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handles_store_entities_failure(self, mock_session):
        """If storing entities fails, rollback and return False."""
        article = self._make_article()

        extraction = {
            "summary": "ok",
            "topics": [],
            "key_facts": [],
            "entities": [{"name": "X", "type": "company", "sentiment": 0, "relevance": 0.5, "context": "ctx"}],
        }

        with (
            patch(
                "app.services.analyzer.extract_entities",
                new_callable=AsyncMock,
                return_value=extraction,
            ),
            patch(
                "app.services.analyzer.store_article_entities",
                new_callable=AsyncMock,
                side_effect=Exception("DB constraint violation"),
            ),
        ):
            result = await analyze_article(mock_session, article)

        assert result is False
        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_entities_still_commits(self, mock_session):
        """An article with no entities should still succeed (summary only)."""
        article = self._make_article()

        extraction = {
            "summary": "A brief note.",
            "topics": ["misc"],
            "key_facts": [],
            "entities": [],
        }

        with (
            patch(
                "app.services.analyzer.extract_entities",
                new_callable=AsyncMock,
                return_value=extraction,
            ),
            patch(
                "app.services.analyzer.store_article_entities",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.analyzer.update_relationships",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_graph,
        ):
            result = await analyze_article(mock_session, article)

        assert result is True
        mock_graph.assert_awaited_once_with(mock_session, [])
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_graph_builder_called_with_entity_ids(self, mock_session):
        """Verify entity IDs from article_entities are passed to update_relationships."""
        article = self._make_article()
        id1, id2 = uuid.uuid4(), uuid.uuid4()

        ae1 = MagicMock()
        ae1.entity_id = id1
        ae2 = MagicMock()
        ae2.entity_id = id2

        extraction = {
            "summary": "ok",
            "topics": [],
            "key_facts": [],
            "entities": [
                {"name": "A", "type": "person", "sentiment": 0, "relevance": 0.5, "context": "a"},
                {"name": "B", "type": "company", "sentiment": 0, "relevance": 0.5, "context": "b"},
            ],
        }

        with (
            patch("app.services.analyzer.extract_entities", new_callable=AsyncMock, return_value=extraction),
            patch("app.services.analyzer.store_article_entities", new_callable=AsyncMock, return_value=[ae1, ae2]),
            patch("app.services.analyzer.update_relationships", new_callable=AsyncMock, return_value=1) as mock_graph,
        ):
            await analyze_article(mock_session, article)

        mock_graph.assert_awaited_once_with(mock_session, [id1, id2])
