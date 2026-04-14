from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity, EntityRelationship
from app.schemas.entity import (
    ConnectionEdge,
    ConnectionNode,
    ConnectionsResponse,
    EntityArticleItem,
    EntityArticleSource,
    EntityDetailResponse,
    EntityResponse,
)

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.get("")
async def list_entities(
    type: str | None = None,
    search: str | None = None,
    min_articles: int | None = None,
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    query = select(Entity)
    count_query = select(func.count(Entity.id))

    if type:
        query = query.where(Entity.type == type)
        count_query = count_query.where(Entity.type == type)
    if search:
        pattern = f"%{search}%"
        query = query.where(Entity.name.ilike(pattern))
        count_query = count_query.where(Entity.name.ilike(pattern))
    if min_articles is not None:
        query = query.where(Entity.article_count >= min_articles)
        count_query = count_query.where(Entity.article_count >= min_articles)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Entity.article_count.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    entities = result.scalars().all()

    return {
        "data": [EntityResponse.model_validate(e).model_dump() for e in entities],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/{entity_id}")
async def get_entity(entity_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    articles_result = await session.execute(
        select(Article)
        .options(selectinload(Article.source))
        .join(ArticleEntity, ArticleEntity.article_id == Article.id)
        .where(ArticleEntity.entity_id == entity_id)
        .order_by(Article.published_at.desc().nullslast())
        .limit(20)
    )
    articles = articles_result.scalars().all()

    return {
        "data": EntityDetailResponse(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            description=entity.description,
            article_count=entity.article_count,
            articles=[
                EntityArticleItem(
                    id=a.id,
                    title=a.title,
                    source=EntityArticleSource(
                        id=a.source.id, name=a.source.name,
                    ),
                    published_at=a.published_at,
                    analyzed=a.analyzed,
                    ingested_at=a.ingested_at,
                )
                for a in articles
            ],
        ).model_dump()
    }


@router.get("/{entity_id}/connections")
async def get_connections(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Entity).where(Entity.id == entity_id))
    center_entity = result.scalar_one_or_none()
    if not center_entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get direct connections (1 hop)
    rel_result = await session.execute(
        select(EntityRelationship)
        .where(
            or_(
                EntityRelationship.entity_a_id == entity_id,
                EntityRelationship.entity_b_id == entity_id,
            )
        )
        .order_by(EntityRelationship.strength.desc())
        .limit(30)
    )
    rels = rel_result.scalars().all()

    connected_ids = set()
    edges = []
    for r in rels:
        other_id = r.entity_b_id if r.entity_a_id == entity_id else r.entity_a_id
        connected_ids.add(other_id)
        edges.append(
            ConnectionEdge(
                source=r.entity_a_id,
                target=r.entity_b_id,
                strength=r.strength,
                evidence_count=r.evidence_count,
            )
        )

    # Get 2nd hop connections
    if connected_ids:
        hop2_result = await session.execute(
            select(EntityRelationship)
            .where(
                or_(
                    EntityRelationship.entity_a_id.in_(connected_ids),
                    EntityRelationship.entity_b_id.in_(connected_ids),
                ),
                ~or_(
                    EntityRelationship.entity_a_id == entity_id,
                    EntityRelationship.entity_b_id == entity_id,
                ),
            )
            .order_by(EntityRelationship.strength.desc())
            .limit(30)
        )
        hop2_rels = hop2_result.scalars().all()
        for r in hop2_rels:
            connected_ids.add(r.entity_a_id)
            connected_ids.add(r.entity_b_id)
            edges.append(
                ConnectionEdge(
                    source=r.entity_a_id,
                    target=r.entity_b_id,
                    strength=r.strength,
                    evidence_count=r.evidence_count,
                )
            )

    connected_ids.discard(entity_id)

    if connected_ids:
        ent_result = await session.execute(
            select(Entity).where(Entity.id.in_(connected_ids))
        )
        connected_entities = ent_result.scalars().all()
    else:
        connected_entities = []

    return {
        "data": ConnectionsResponse(
            center=ConnectionNode(
                id=center_entity.id,
                name=center_entity.name,
                type=center_entity.type,
                article_count=center_entity.article_count,
            ),
            nodes=[
                ConnectionNode(
                    id=e.id, name=e.name, type=e.type, article_count=e.article_count
                )
                for e in connected_entities
            ],
            edges=edges,
        ).model_dump()
    }
