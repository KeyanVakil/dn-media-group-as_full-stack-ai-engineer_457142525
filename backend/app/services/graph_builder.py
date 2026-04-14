"""Co-occurrence graph builder.

After entity extraction, processes all entity pairs in an article to create
or update relationship records. Strength is normalized: min(1.0, evidence_count / 10).
"""

import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.entity import EntityRelationship

logger = logging.getLogger(__name__)


async def update_relationships(
    session: AsyncSession,
    entity_ids: list[UUID],
) -> int:
    """Create or strengthen relationships between all entity pairs that co-occur in an article.

    Returns the number of relationships updated or created.
    """
    if len(entity_ids) < 2:
        return 0

    updated = 0
    pairs_seen: set[tuple[UUID, UUID]] = set()

    for i, a_id in enumerate(entity_ids):
        for b_id in entity_ids[i + 1 :]:
            pair = (min(a_id, b_id), max(a_id, b_id))
            if pair in pairs_seen:
                continue
            pairs_seen.add(pair)

            result = await session.execute(
                select(EntityRelationship).where(
                    and_(
                        EntityRelationship.entity_a_id == pair[0],
                        EntityRelationship.entity_b_id == pair[1],
                    )
                )
            )
            rel = result.scalar_one_or_none()

            if rel is None:
                rel = EntityRelationship(
                    entity_a_id=pair[0],
                    entity_b_id=pair[1],
                    evidence_count=1,
                    strength=min(1.0, 1 / 10),
                )
                session.add(rel)
            else:
                rel.evidence_count += 1
                rel.strength = min(1.0, rel.evidence_count / 10)
                rel.last_seen_at = func.now()

            updated += 1

    await session.flush()
    return updated
