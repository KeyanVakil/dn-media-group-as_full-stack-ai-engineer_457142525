"""Tests for the co-occurrence graph builder.

Covers update_relationships with varying entity counts, strength calculation,
relationship strengthening, and entity_a_id < entity_b_id ordering invariant.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.graph_builder import update_relationships


def _make_uuid() -> uuid.UUID:
    return uuid.uuid4()


class TestUpdateRelationships:
    """Test suite for update_relationships."""

    @pytest.mark.asyncio
    async def test_zero_entities_returns_zero(self, mock_session):
        """No entities means no relationships to create."""
        count = await update_relationships(mock_session, [])
        assert count == 0
        mock_session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_one_entity_returns_zero(self, mock_session):
        """A single entity cannot form a pair."""
        count = await update_relationships(mock_session, [_make_uuid()])
        assert count == 0
        mock_session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_two_entities_creates_one_relationship(self, mock_session):
        """Two entities should produce exactly one co-occurrence relationship."""
        id_a, id_b = _make_uuid(), _make_uuid()

        # No existing relationship
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        count = await update_relationships(mock_session, [id_a, id_b])

        assert count == 1
        mock_session.add.assert_called_once()
        added_rel = mock_session.add.call_args[0][0]

        # Verify ordering invariant: entity_a_id < entity_b_id
        assert added_rel.entity_a_id < added_rel.entity_b_id
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_three_entities_creates_three_relationships(self, mock_session):
        """Three entities = C(3,2) = 3 pairs."""
        ids = [_make_uuid() for _ in range(3)]

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        count = await update_relationships(mock_session, ids)

        assert count == 3
        assert mock_session.add.call_count == 3

    @pytest.mark.asyncio
    async def test_four_entities_creates_six_relationships(self, mock_session):
        """Four entities = C(4,2) = 6 pairs."""
        ids = [_make_uuid() for _ in range(4)]

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        count = await update_relationships(mock_session, ids)
        assert count == 6

    @pytest.mark.asyncio
    async def test_strength_calculation_new_relationship(self, mock_session):
        """New relationship: evidence_count=1, strength=min(1.0, 1/10) = 0.1."""
        id_a, id_b = _make_uuid(), _make_uuid()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        await update_relationships(mock_session, [id_a, id_b])

        added_rel = mock_session.add.call_args[0][0]
        assert added_rel.evidence_count == 1
        assert added_rel.strength == pytest.approx(0.1)

    @pytest.mark.asyncio
    async def test_existing_relationship_is_strengthened(self, mock_session):
        """When a relationship already exists, evidence_count increments and strength updates."""
        id_a, id_b = sorted([_make_uuid(), _make_uuid()])

        existing_rel = MagicMock()
        existing_rel.entity_a_id = id_a
        existing_rel.entity_b_id = id_b
        existing_rel.evidence_count = 4
        existing_rel.strength = 0.4

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_rel
        mock_session.execute = AsyncMock(return_value=result_mock)

        count = await update_relationships(mock_session, [id_a, id_b])

        assert count == 1
        assert existing_rel.evidence_count == 5
        assert existing_rel.strength == pytest.approx(0.5)
        # Existing relationship is updated in-place, not added again
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_strength_caps_at_one(self, mock_session):
        """Strength should never exceed 1.0, even with evidence_count > 10."""
        id_a, id_b = sorted([_make_uuid(), _make_uuid()])

        existing_rel = MagicMock()
        existing_rel.entity_a_id = id_a
        existing_rel.entity_b_id = id_b
        existing_rel.evidence_count = 12
        existing_rel.strength = 1.0

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_rel
        mock_session.execute = AsyncMock(return_value=result_mock)

        await update_relationships(mock_session, [id_a, id_b])

        assert existing_rel.evidence_count == 13
        assert existing_rel.strength == 1.0  # min(1.0, 13/10) = 1.0

    @pytest.mark.asyncio
    async def test_ordering_invariant_maintained(self, mock_session):
        """Regardless of input order, entity_a_id < entity_b_id in the created relationship."""
        id_small = uuid.UUID("00000000-0000-0000-0000-000000000001")
        id_large = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        # Pass in reversed order: large first
        await update_relationships(mock_session, [id_large, id_small])

        added_rel = mock_session.add.call_args[0][0]
        assert added_rel.entity_a_id == id_small
        assert added_rel.entity_b_id == id_large

    @pytest.mark.asyncio
    async def test_duplicate_ids_in_list(self, mock_session):
        """Duplicate entity IDs should still produce correct pair count (no self-pairs)."""
        id_a = _make_uuid()
        id_b = _make_uuid()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        # Pass [a, b, a] -- pairs: (a,b), (a,a), (b,a) but (a,a) deduped, (b,a)==(a,b) deduped
        count = await update_relationships(mock_session, [id_a, id_b, id_a])

        # Pairs enumerated: (a,b), (a,a), (b,a)
        # After min/max ordering: (a,b), (a,a), (a,b)
        # Dedup via pairs_seen: (a,b) and (a,a) = 2 unique pairs
        assert count == 2

    @pytest.mark.asyncio
    async def test_last_seen_at_updated_on_existing(self, mock_session):
        """When strengthening an existing relationship, last_seen_at should be updated."""
        id_a, id_b = sorted([_make_uuid(), _make_uuid()])

        existing_rel = MagicMock()
        existing_rel.entity_a_id = id_a
        existing_rel.entity_b_id = id_b
        existing_rel.evidence_count = 2
        existing_rel.strength = 0.2
        existing_rel.last_seen_at = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_rel
        mock_session.execute = AsyncMock(return_value=result_mock)

        await update_relationships(mock_session, [id_a, id_b])

        # last_seen_at should have been set (to func.now())
        assert existing_rel.last_seen_at is not None
