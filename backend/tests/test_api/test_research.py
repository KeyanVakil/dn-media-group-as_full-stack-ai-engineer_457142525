"""Tests for the research API endpoints.

Uses httpx AsyncClient with mocked database session to test:
- POST /api/research (create a research task)
- GET /api/research (list tasks)
- GET /api/research/:id (task detail with steps)
- 404 handling for missing tasks
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCreateResearch:
    """POST /api/research"""

    @pytest.mark.asyncio
    async def test_creates_research_task(self, client, mock_session):
        """Should create a task, return 201, and trigger background research."""
        task_id = uuid.uuid4()
        created_at = datetime(2026, 4, 1, tzinfo=timezone.utc)

        # After session.refresh, the task should have an id and created_at
        async def mock_refresh(obj):
            obj.id = task_id
            obj.created_at = created_at
            obj.status = "pending"
            obj.completed_at = None

        mock_session.refresh = AsyncMock(side_effect=mock_refresh)

        # Mock the background task to avoid it connecting to a real database
        with patch("app.api.research._run_research_background", new_callable=AsyncMock):
            response = await client.post(
                "/api/research",
                json={"query": "What is the impact of AI on markets?"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["data"]["query"] == "What is the impact of AI on markets?"
        assert body["data"]["status"] == "pending"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_empty_query(self, client, mock_session):
        """Should reject a research request with an empty query."""
        response = await client.post("/api/research", json={"query": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_missing_query(self, client, mock_session):
        """Should reject a request without the query field."""
        response = await client.post("/api/research", json={})
        assert response.status_code == 422


class TestListResearch:
    """GET /api/research"""

    @pytest.mark.asyncio
    async def test_returns_paginated_list(self, client, mock_session, sample_research_task):
        """Should return research tasks with pagination."""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_research_task]
        tasks_result = MagicMock()
        tasks_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, tasks_result])

        response = await client.get("/api/research")

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["total"] == 1
        assert len(body["data"]) == 1
        assert body["data"][0]["query"] == "What is the impact of AI on financial markets?"
        assert body["data"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client, mock_session):
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        tasks_result = MagicMock()
        tasks_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, tasks_result])

        response = await client.get("/api/research")
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_pagination_params(self, client, mock_session):
        count_result = MagicMock()
        count_result.scalar.return_value = 50

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        tasks_result = MagicMock()
        tasks_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, tasks_result])

        response = await client.get("/api/research", params={"limit": 5, "offset": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["limit"] == 5
        assert body["meta"]["offset"] == 10


class TestGetResearch:
    """GET /api/research/:id"""

    @pytest.mark.asyncio
    async def test_returns_task_with_steps(
        self, client, mock_session, sample_research_task, sample_research_step
    ):
        """Should return research task detail with steps."""
        sample_research_task.steps = [sample_research_step]

        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = sample_research_task
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        response = await client.get(f"/api/research/{sample_research_task.id}")

        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        assert data["query"] == "What is the impact of AI on financial markets?"
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert len(data["steps"]) == 1
        assert data["steps"][0]["action"] == "parse_query"
        assert data["steps"][0]["step_number"] == 1

    @pytest.mark.asyncio
    async def test_returns_task_without_steps(self, client, mock_session, sample_research_task):
        """Task with no steps yet should still be returned."""
        sample_research_task.steps = []
        sample_research_task.status = "pending"
        sample_research_task.result = None

        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = sample_research_task
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        response = await client.get(f"/api/research/{sample_research_task.id}")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "pending"
        assert data["steps"] == []
        assert data["result"] is None

    @pytest.mark.asyncio
    async def test_404_for_missing_task(self, client, mock_session):
        """Should return 404 when task is not found."""
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        fake_id = uuid.uuid4()
        response = await client.get(f"/api/research/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Research task not found"

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client, mock_session):
        response = await client.get("/api/research/not-a-uuid")
        assert response.status_code == 422
