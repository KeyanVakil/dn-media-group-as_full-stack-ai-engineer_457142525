"""Tests for the entities API endpoints.

Uses httpx AsyncClient with mocked database session to test:
- GET /api/entities (paginated list, type filter, search)
- GET /api/entities/:id (entity detail)
- GET /api/entities/:id/connections (graph data)
- 404 handling for missing entities
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestListEntities:
    """GET /api/entities"""

    @pytest.mark.asyncio
    async def test_returns_paginated_list(self, client, mock_session, sample_entity):
        """Should return entities with pagination metadata."""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_entity]
        entities_result = MagicMock()
        entities_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, entities_result])

        response = await client.get("/api/entities")

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["total"] == 1
        assert len(body["data"]) == 1
        assert body["data"][0]["name"] == "Google"
        assert body["data"][0]["type"] == "company"

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client, mock_session):
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        entities_result = MagicMock()
        entities_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, entities_result])

        response = await client.get("/api/entities")
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_type_filter(self, client, mock_session, sample_entity):
        """Should filter entities by type."""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_entity]
        entities_result = MagicMock()
        entities_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, entities_result])

        response = await client.get("/api/entities", params={"type": "company"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 1

    @pytest.mark.asyncio
    async def test_search_filter(self, client, mock_session, sample_entity):
        """Should filter entities by name search."""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_entity]
        entities_result = MagicMock()
        entities_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, entities_result])

        response = await client.get("/api/entities", params={"search": "Goo"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_min_articles_filter(self, client, mock_session, sample_entity):
        """Should filter entities by minimum article count."""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sample_entity]
        entities_result = MagicMock()
        entities_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, entities_result])

        response = await client.get("/api/entities", params={"min_articles": 5})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_params(self, client, mock_session):
        """Should respect limit and offset."""
        count_result = MagicMock()
        count_result.scalar.return_value = 100

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        entities_result = MagicMock()
        entities_result.scalars.return_value = scalars_mock

        mock_session.execute = AsyncMock(side_effect=[count_result, entities_result])

        response = await client.get("/api/entities", params={"limit": 5, "offset": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["limit"] == 5
        assert body["meta"]["offset"] == 10


class TestGetEntity:
    """GET /api/entities/:id"""

    @pytest.mark.asyncio
    async def test_returns_entity_detail(
        self, client, mock_session, sample_entity, sample_article
    ):
        """Should return the entity data with related articles."""
        # First call: entity lookup
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = sample_entity

        # Second call: related articles query
        articles_scalars = MagicMock()
        articles_scalars.all.return_value = [sample_article]
        articles_result = MagicMock()
        articles_result.scalars.return_value = articles_scalars

        mock_session.execute = AsyncMock(
            side_effect=[scalar_mock, articles_result]
        )

        response = await client.get(f"/api/entities/{sample_entity.id}")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Google"
        assert data["type"] == "company"
        assert data["article_count"] == 15
        assert len(data["articles"]) == 1
        assert data["articles"][0]["title"] == "Tech Giant Acquires AI Startup"

    @pytest.mark.asyncio
    async def test_404_for_missing_entity(self, client, mock_session):
        """Should return 404 for non-existent entity."""
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        fake_id = uuid.uuid4()
        response = await client.get(f"/api/entities/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Entity not found"

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client, mock_session):
        response = await client.get("/api/entities/not-a-uuid")
        assert response.status_code == 422


class TestGetConnections:
    """GET /api/entities/:id/connections"""

    @pytest.mark.asyncio
    async def test_returns_graph_data(self, client, mock_session, sample_entity):
        """Should return center node, connected nodes, and edges."""
        other_entity = MagicMock()
        other_entity.id = uuid.uuid4()
        other_entity.name = "Apple"
        other_entity.type = "company"
        other_entity.article_count = 20

        rel = MagicMock()
        rel.entity_a_id = min(sample_entity.id, other_entity.id)
        rel.entity_b_id = max(sample_entity.id, other_entity.id)
        rel.strength = 0.5
        rel.evidence_count = 5

        # First: center entity lookup
        center_result = MagicMock()
        center_result.scalar_one_or_none.return_value = sample_entity

        # Second: 1st hop relationships
        rel_scalars = MagicMock()
        rel_scalars.all.return_value = [rel]
        rel_result = MagicMock()
        rel_result.scalars.return_value = rel_scalars

        # Third: 2nd hop relationships
        hop2_scalars = MagicMock()
        hop2_scalars.all.return_value = []
        hop2_result = MagicMock()
        hop2_result.scalars.return_value = hop2_scalars

        # Fourth: connected entities
        ent_scalars = MagicMock()
        ent_scalars.all.return_value = [other_entity]
        ent_result = MagicMock()
        ent_result.scalars.return_value = ent_scalars

        mock_session.execute = AsyncMock(
            side_effect=[center_result, rel_result, hop2_result, ent_result]
        )

        response = await client.get(f"/api/entities/{sample_entity.id}/connections")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["center"]["name"] == "Google"
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "Apple"
        assert len(data["edges"]) == 1
        assert data["edges"][0]["strength"] == 0.5

    @pytest.mark.asyncio
    async def test_returns_empty_connections(self, client, mock_session, sample_entity):
        """Entity with no connections should return empty nodes and edges."""
        center_result = MagicMock()
        center_result.scalar_one_or_none.return_value = sample_entity

        rel_scalars = MagicMock()
        rel_scalars.all.return_value = []
        rel_result = MagicMock()
        rel_result.scalars.return_value = rel_scalars

        mock_session.execute = AsyncMock(side_effect=[center_result, rel_result])

        response = await client.get(f"/api/entities/{sample_entity.id}/connections")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["center"]["name"] == "Google"
        assert data["nodes"] == []
        assert data["edges"] == []

    @pytest.mark.asyncio
    async def test_404_for_missing_entity(self, client, mock_session):
        """Should return 404 if entity not found."""
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=scalar_mock)

        fake_id = uuid.uuid4()
        response = await client.get(f"/api/entities/{fake_id}/connections")
        assert response.status_code == 404
