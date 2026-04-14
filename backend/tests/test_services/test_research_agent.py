"""Tests for the multi-step research agent.

Covers individual tool executors with mock data, the record_step helper,
and the overall agent orchestration flow with mocked Claude responses.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research_agent import (
    TOOL_EXECUTORS,
    _exec_get_article_detail,
    _exec_get_connections,
    _exec_get_entity,
    _exec_search_articles,
    record_step,
    run_research,
)


# ---------------------------------------------------------------------------
# Tool executor tests
# ---------------------------------------------------------------------------


class TestExecSearchArticles:
    @pytest.mark.asyncio
    async def test_returns_matching_articles(self, mock_session):
        """Search should return formatted article dicts."""
        article = MagicMock()
        article.id = uuid.uuid4()
        article.title = "AI in Finance"
        article.published_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
        article.summary = MagicMock()
        article.summary.summary = "AI is transforming finance."

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [article]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute = AsyncMock(return_value=result_mock)

        result = await _exec_search_articles(mock_session, "AI", limit=5)

        assert result["article_count"] == 1
        assert result["articles"][0]["title"] == "AI in Finance"
        assert result["articles"][0]["summary"] == "AI is transforming finance."

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_matches(self, mock_session):
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute = AsyncMock(return_value=result_mock)

        result = await _exec_search_articles(mock_session, "nonexistent")
        assert result["article_count"] == 0
        assert result["articles"] == []

    @pytest.mark.asyncio
    async def test_handles_article_without_summary(self, mock_session):
        article = MagicMock()
        article.id = uuid.uuid4()
        article.title = "No Summary Article"
        article.published_at = None
        article.summary = None

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [article]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute = AsyncMock(return_value=result_mock)

        result = await _exec_search_articles(mock_session, "test")
        assert result["articles"][0]["summary"] is None
        assert result["articles"][0]["published_at"] is None


class TestExecGetEntity:
    @pytest.mark.asyncio
    async def test_returns_entity_with_articles(self, mock_session):
        entity = MagicMock()
        entity.id = uuid.uuid4()
        entity.name = "Apple"
        entity.type = "company"
        entity.article_count = 10

        article = MagicMock()
        article.id = uuid.uuid4()
        article.title = "Apple Q2 Earnings"

        # First execute: entity search; second: articles
        entity_scalars = MagicMock()
        entity_scalars.all.return_value = [entity]
        entity_result = MagicMock()
        entity_result.scalars.return_value = entity_scalars

        article_scalars = MagicMock()
        article_scalars.all.return_value = [article]
        article_result = MagicMock()
        article_result.scalars.return_value = article_scalars

        mock_session.execute = AsyncMock(side_effect=[entity_result, article_result])

        result = await _exec_get_entity(mock_session, "Apple")

        assert result["found"] is True
        assert result["entity"]["name"] == "Apple"
        assert len(result["recent_articles"]) == 1

    @pytest.mark.asyncio
    async def test_returns_not_found(self, mock_session):
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute = AsyncMock(return_value=result_mock)

        result = await _exec_get_entity(mock_session, "Nonexistent Corp")
        assert result["found"] is False


class TestExecGetConnections:
    @pytest.mark.asyncio
    async def test_returns_connections(self, mock_session):
        entity_id = uuid.uuid4()
        other_id = uuid.uuid4()

        rel = MagicMock()
        rel.entity_a_id = min(entity_id, other_id)
        rel.entity_b_id = max(entity_id, other_id)
        rel.strength = 0.5
        rel.evidence_count = 5

        other_entity = MagicMock()
        other_entity.id = other_id
        other_entity.name = "Partner Corp"
        other_entity.type = "company"

        # First execute: relationships; second: entities
        rel_scalars = MagicMock()
        rel_scalars.all.return_value = [rel]
        rel_result = MagicMock()
        rel_result.scalars.return_value = rel_scalars

        ent_scalars = MagicMock()
        ent_scalars.all.return_value = [other_entity]
        ent_result = MagicMock()
        ent_result.scalars.return_value = ent_scalars

        mock_session.execute = AsyncMock(side_effect=[rel_result, ent_result])

        result = await _exec_get_connections(mock_session, str(entity_id))
        assert len(result["connections"]) == 1
        assert result["connections"][0]["entity"]["name"] == "Partner Corp"

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_error(self, mock_session):
        result = await _exec_get_connections(mock_session, "not-a-uuid")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_connections_returns_empty(self, mock_session):
        entity_id = uuid.uuid4()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute = AsyncMock(return_value=result_mock)

        result = await _exec_get_connections(mock_session, str(entity_id))
        assert result["connections"] == []


class TestExecGetArticleDetail:
    @pytest.mark.asyncio
    async def test_returns_article_with_entities(self, mock_session):
        article_id = uuid.uuid4()

        ae = MagicMock()
        ae.entity = MagicMock()
        ae.entity.name = "Tesla"
        ae.entity.type = "company"
        ae.sentiment = 0.7

        article = MagicMock()
        article.id = article_id
        article.title = "Tesla Earnings"
        article.content = "Tesla reported strong Q2 earnings..." * 100  # long content
        article.published_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
        article.summary = MagicMock()
        article.summary.summary = "Tesla had a great quarter."
        article.article_entities = [ae]

        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = article
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        result = await _exec_get_article_detail(mock_session, str(article_id))

        assert result["title"] == "Tesla Earnings"
        assert len(result["content"]) <= 3000
        assert result["entities"][0]["name"] == "Tesla"

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_error(self, mock_session):
        result = await _exec_get_article_detail(mock_session, "bad-uuid")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_article_not_found(self, mock_session):
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        result = await _exec_get_article_detail(mock_session, str(uuid.uuid4()))
        assert result["error"] == "Article not found"


# ---------------------------------------------------------------------------
# record_step
# ---------------------------------------------------------------------------


class TestRecordStep:
    @pytest.mark.asyncio
    async def test_creates_and_flushes_step(self, mock_session):
        task_id = uuid.uuid4()
        step = await record_step(
            mock_session,
            task_id=task_id,
            step_number=1,
            action="search_articles",
            input_data={"query": "AI"},
            output_data={"article_count": 5},
        )

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.task_id == task_id
        assert added.step_number == 1
        assert added.action == "search_articles"
        mock_session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# run_research (full orchestration)
# ---------------------------------------------------------------------------


class TestRunResearch:
    @pytest.mark.asyncio
    async def test_synthesize_tool_ends_research(self, mock_session):
        """When Claude calls the synthesize tool, research should complete."""
        task = MagicMock()
        task.id = uuid.uuid4()
        task.query = "What is happening with oil prices?"
        task.status = "pending"
        task.result = None
        task.steps = []

        # Claude response with synthesize tool call
        synth_block = MagicMock()
        synth_block.type = "tool_use"
        synth_block.name = "synthesize"
        synth_block.id = "tool_1"
        synth_block.input = {
            "briefing": "Oil prices are rising due to supply constraints.",
            "key_findings": ["Brent up 5%", "OPEC cuts production"],
            "evidence": [{"article_id": "abc", "title": "Oil Surge", "relevance": "high"}],
            "follow_up_questions": ["Will OPEC increase output?"],
        }

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [synth_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        result = await run_research(mock_session, task, client=mock_client)

        assert result.status == "completed"
        assert result.result is not None
        assert result.result["briefing"] == "Oil prices are rising due to supply constraints."
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_tool_execution_before_synthesize(self, mock_session):
        """Claude calls search_articles, then synthesize on the second turn."""
        task = MagicMock()
        task.id = uuid.uuid4()
        task.query = "AI market trends"
        task.status = "pending"
        task.result = None
        task.steps = []

        # First response: Claude calls search_articles
        search_block = MagicMock()
        search_block.type = "tool_use"
        search_block.name = "search_articles"
        search_block.id = "tool_search_1"
        search_block.input = {"query": "AI market", "limit": 5}

        response1 = MagicMock()
        response1.stop_reason = "tool_use"
        response1.content = [search_block]

        # Second response: Claude calls synthesize
        synth_block = MagicMock()
        synth_block.type = "tool_use"
        synth_block.name = "synthesize"
        synth_block.id = "tool_synth_1"
        synth_block.input = {
            "briefing": "AI market is booming.",
            "key_findings": ["Investment up 200%"],
            "evidence": [],
            "follow_up_questions": [],
        }

        response2 = MagicMock()
        response2.stop_reason = "tool_use"
        response2.content = [synth_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=[response1, response2])

        # Mock the search_articles executor
        search_output = {"article_count": 2, "articles": [{"id": "1", "title": "AI Boom"}]}

        with patch.dict(
            "app.services.research_agent.TOOL_EXECUTORS",
            {"search_articles": AsyncMock(return_value=search_output)},
        ):
            result = await run_research(mock_session, task, client=mock_client)

        assert result.status == "completed"
        assert mock_client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_end_turn_without_synthesize(self, mock_session):
        """If Claude returns end_turn without calling synthesize, use text as briefing."""
        task = MagicMock()
        task.id = uuid.uuid4()
        task.query = "Simple question"
        task.status = "pending"
        task.result = None
        task.steps = []

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Based on my analysis, here is the answer."

        response = MagicMock()
        response.stop_reason = "end_turn"
        response.content = [text_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        result = await run_research(mock_session, task, client=mock_client)

        assert result.status == "completed"
        assert result.result is not None
        assert "Based on my analysis" in result.result["briefing"]

    @pytest.mark.asyncio
    async def test_sets_status_to_running_and_completed(self, mock_session):
        """Task status should progress from pending -> running -> completed."""
        status_log = []

        class TrackedTask:
            """Simple object that records status transitions."""

            def __init__(self):
                self.id = uuid.uuid4()
                self.query = "Test"
                self._status = "pending"
                self.result = None
                self.steps = []
                self.completed_at = None

            @property
            def status(self):
                return self._status

            @status.setter
            def status(self, value):
                status_log.append(value)
                self._status = value

        task = TrackedTask()

        synth_block = MagicMock()
        synth_block.type = "tool_use"
        synth_block.name = "synthesize"
        synth_block.id = "t1"
        synth_block.input = {
            "briefing": "Done",
            "key_findings": [],
            "evidence": [],
            "follow_up_questions": [],
        }

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [synth_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        await run_research(mock_session, task, client=mock_client)

        assert status_log == ["running", "completed"]

    @pytest.mark.asyncio
    async def test_max_iterations_prevents_infinite_loop(self, mock_session):
        """Agent should stop after max_iterations even without synthesize."""
        task = MagicMock()
        task.id = uuid.uuid4()
        task.query = "Infinite loop test"
        task.status = "pending"
        task.result = None
        task.steps = []

        # Claude always calls search_articles, never synthesizes
        search_block = MagicMock()
        search_block.type = "tool_use"
        search_block.name = "search_articles"
        search_block.id = "t1"
        search_block.input = {"query": "loop"}

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [search_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        search_output = {"article_count": 0, "articles": []}

        with patch.dict(
            "app.services.research_agent.TOOL_EXECUTORS",
            {"search_articles": AsyncMock(return_value=search_output)},
        ):
            result = await run_research(mock_session, task, client=mock_client)

        # Should have called create at most 10 times (max_iterations)
        assert mock_client.messages.create.await_count <= 10
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_parse_query_step_recorded_first(self, mock_session):
        """The first step recorded should be parse_query."""
        task = MagicMock()
        task.id = uuid.uuid4()
        task.query = "Test query"
        task.status = "pending"
        task.result = None
        task.steps = []

        synth_block = MagicMock()
        synth_block.type = "tool_use"
        synth_block.name = "synthesize"
        synth_block.id = "t1"
        synth_block.input = {
            "briefing": "Done",
            "key_findings": [],
            "evidence": [],
            "follow_up_questions": [],
        }

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [synth_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=response)

        await run_research(mock_session, task, client=mock_client)

        # Check that session.add was called with a ResearchStep having action="parse_query"
        add_calls = mock_session.add.call_args_list
        first_step = add_calls[0][0][0]
        assert first_step.action == "parse_query"
        assert first_step.step_number == 1


class TestToolExecutorsMapping:
    """Verify the TOOL_EXECUTORS dict contains expected tools."""

    def test_contains_search_articles(self):
        assert "search_articles" in TOOL_EXECUTORS

    def test_contains_get_entity(self):
        assert "get_entity" in TOOL_EXECUTORS

    def test_contains_get_connections(self):
        assert "get_connections" in TOOL_EXECUTORS

    def test_contains_get_article_detail(self):
        assert "get_article_detail" in TOOL_EXECUTORS

    def test_synthesize_not_in_executors(self):
        """Synthesize is handled specially, not via TOOL_EXECUTORS."""
        assert "synthesize" not in TOOL_EXECUTORS
