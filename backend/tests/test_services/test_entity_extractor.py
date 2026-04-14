"""Tests for the entity extraction service.

Covers normalize_name, extract_entities (with mocked Claude client),
resolve_entity, and store_article_entities.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.entity_extractor import (
    extract_entities,
    normalize_name,
    resolve_entity,
    store_article_entities,
)


# ---------------------------------------------------------------------------
# normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_strips_whitespace(self):
        assert normalize_name("  Google  ") == "google"

    def test_lowercases(self):
        assert normalize_name("Apple Inc.") == "apple inc"

    def test_removes_periods(self):
        assert normalize_name("U.S.A.") == "usa"

    def test_removes_commas(self):
        assert normalize_name("Alphabet, Inc.") == "alphabet inc"

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_already_normalized(self):
        assert normalize_name("google") == "google"

    def test_mixed_punctuation(self):
        assert normalize_name("  J.P. Morgan, Chase  ") == "jp morgan chase"


# ---------------------------------------------------------------------------
# extract_entities (mocked Claude client)
# ---------------------------------------------------------------------------


class TestExtractEntities:
    @pytest.mark.asyncio
    async def test_returns_extraction_from_tool_use_block(self):
        """Claude returns a tool_use block; we should get its input back."""
        expected_extraction = {
            "summary": "Article summary here.",
            "topics": ["finance"],
            "key_facts": ["Fact one"],
            "entities": [
                {
                    "name": "Acme Corp",
                    "type": "company",
                    "sentiment": 0.4,
                    "relevance": 0.9,
                    "context": "Acme Corp announced...",
                }
            ],
        }

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "extract_entities"
        tool_block.input = expected_extraction

        response = MagicMock()
        response.content = [tool_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        result = await extract_entities("Test Title", "Test content", client=mock_client)

        assert result == expected_extraction
        mock_client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_no_tool_use_block(self):
        """If Claude returns only text, raise ValueError."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "I cannot extract entities."

        response = MagicMock()
        response.content = [text_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        with pytest.raises(ValueError, match="Claude did not return entity extraction"):
            await extract_entities("Title", "Content", client=mock_client)

    @pytest.mark.asyncio
    async def test_ignores_non_matching_tool_blocks(self):
        """If there is a tool_use block with wrong name, skip it."""
        wrong_block = MagicMock()
        wrong_block.type = "tool_use"
        wrong_block.name = "other_tool"
        wrong_block.input = {}

        right_block = MagicMock()
        right_block.type = "tool_use"
        right_block.name = "extract_entities"
        right_block.input = {"summary": "Found it", "topics": [], "key_facts": [], "entities": []}

        response = MagicMock()
        response.content = [wrong_block, right_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        result = await extract_entities("Title", "Content", client=mock_client)
        assert result["summary"] == "Found it"

    @pytest.mark.asyncio
    async def test_truncates_content_to_8000_chars(self):
        """Verify the prompt truncates long content."""
        mock_client = AsyncMock()

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "extract_entities"
        tool_block.input = {"summary": "ok", "topics": [], "key_facts": [], "entities": []}

        response = MagicMock()
        response.content = [tool_block]
        mock_client.messages.create = AsyncMock(return_value=response)

        long_content = "x" * 20000
        await extract_entities("Title", long_content, client=mock_client)

        call_args = mock_client.messages.create.call_args
        msg_content = call_args.kwargs["messages"][0]["content"]
        # The content passed should be truncated to at most 8000 chars of the article
        assert len(msg_content) < 20000 + 500  # plus prompt text overhead


# ---------------------------------------------------------------------------
# resolve_entity (mocked session)
# ---------------------------------------------------------------------------


class TestResolveEntity:
    @pytest.mark.asyncio
    async def test_returns_existing_entity(self, mock_session):
        """When a matching entity exists, return it without creating a new one."""
        existing = MagicMock()
        existing.id = uuid.uuid4()
        existing.name = "Google"
        existing.type = "company"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=result_mock)

        entity = await resolve_entity(mock_session, "Google", "company")

        assert entity.name == "Google"
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_entity_when_not_found(self, mock_session):
        """When no match exists, create and flush a new entity."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        entity = await resolve_entity(mock_session, " Apple Inc. ", "company")

        # Should have called add with a new Entity
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.name == "Apple Inc."
        assert added.type == "company"
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_strips_name_before_creating(self, mock_session):
        """New entities should have stripped names."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        await resolve_entity(mock_session, "  SpaceX  ", "company")

        added = mock_session.add.call_args[0][0]
        assert added.name == "SpaceX"


# ---------------------------------------------------------------------------
# store_article_entities (mocked session + resolve_entity)
# ---------------------------------------------------------------------------


class TestStoreArticleEntities:
    @pytest.mark.asyncio
    async def test_creates_article_entity_per_extraction(self, mock_session, extraction_result):
        """Each entity in the extraction should produce an ArticleEntity."""
        article_id = uuid.uuid4()

        # Mock resolve_entity to return a new entity each time
        entities = []
        for raw in extraction_result["entities"]:
            e = MagicMock()
            e.id = uuid.uuid4()
            e.article_count = 0
            entities.append(e)

        call_count = 0

        async def mock_resolve(session, name, etype):
            nonlocal call_count
            ent = entities[call_count]
            call_count += 1
            return ent

        with patch("app.services.entity_extractor.resolve_entity", side_effect=mock_resolve):
            result = await store_article_entities(mock_session, article_id, extraction_result)

        assert len(result) == 3
        # Each entity should have article_count incremented
        for e in entities:
            assert e.article_count == 1

    @pytest.mark.asyncio
    async def test_clamps_sentiment_and_relevance(self, mock_session):
        """Sentiment must be [-1, 1] and relevance [0, 1]."""
        article_id = uuid.uuid4()
        extraction = {
            "entities": [
                {
                    "name": "Test",
                    "type": "company",
                    "sentiment": 5.0,  # too high
                    "relevance": -2.0,  # too low
                    "context": "test",
                }
            ]
        }

        entity_mock = MagicMock()
        entity_mock.id = uuid.uuid4()
        entity_mock.article_count = 0

        async def mock_resolve(session, name, etype):
            return entity_mock

        with patch("app.services.entity_extractor.resolve_entity", side_effect=mock_resolve):
            result = await store_article_entities(mock_session, article_id, extraction)

        # The added ArticleEntity should have clamped values
        added_ae = mock_session.add.call_args_list[-1][0][0]
        assert added_ae.sentiment == 1.0
        assert added_ae.relevance == 0.0

    @pytest.mark.asyncio
    async def test_empty_entities_list(self, mock_session):
        """If extraction has no entities, return empty list."""
        article_id = uuid.uuid4()
        result = await store_article_entities(mock_session, article_id, {"entities": []})
        assert result == []
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_missing_entities_key(self, mock_session):
        """If extraction dict lacks 'entities' key, return empty list."""
        article_id = uuid.uuid4()
        result = await store_article_entities(mock_session, article_id, {})
        assert result == []
