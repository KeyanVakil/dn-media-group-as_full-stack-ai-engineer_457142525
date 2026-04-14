from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session, get_session
from app.models.article import Article, ArticleSummary
from app.models.entity import ArticleEntity
from app.schemas.article import (
    ArticleDetailResponse,
    ArticleEntityResponse,
    ArticleListResponse,
    ArticleSourceResponse,
    ArticleSummaryResponse,
)
from app.services.analyzer import analyze_article

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("")
async def list_articles(
    source_id: UUID | None = None,
    topic: str | None = None,
    search: str | None = None,
    analyzed: bool | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    query = select(Article).options(selectinload(Article.source))
    count_query = select(func.count(Article.id))

    if source_id is not None:
        query = query.where(Article.source_id == source_id)
        count_query = count_query.where(Article.source_id == source_id)
    if analyzed is not None:
        query = query.where(Article.analyzed == analyzed)
        count_query = count_query.where(Article.analyzed == analyzed)
    if search:
        pattern = f"%{search}%"
        condition = or_(Article.title.ilike(pattern), Article.content.ilike(pattern))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if from_date:
        query = query.where(Article.published_at >= from_date)
        count_query = count_query.where(Article.published_at >= from_date)
    if to_date:
        query = query.where(Article.published_at <= to_date)
        count_query = count_query.where(Article.published_at <= to_date)
    if topic:
        query = query.join(ArticleSummary, ArticleSummary.article_id == Article.id).where(
            ArticleSummary.topics.contains([topic])
        )
        count_query = count_query.join(
            ArticleSummary, ArticleSummary.article_id == Article.id
        ).where(ArticleSummary.topics.contains([topic]))

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Article.published_at.desc().nullslast()).offset(offset).limit(limit)
    result = await session.execute(query)
    articles = result.scalars().all()

    data = [
        ArticleListResponse(
            id=a.id,
            title=a.title,
            source=ArticleSourceResponse(id=a.source.id, name=a.source.name),
            published_at=a.published_at,
            analyzed=a.analyzed,
            ingested_at=a.ingested_at,
        )
        for a in articles
    ]

    return {
        "data": [d.model_dump() for d in data],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/{article_id}")
async def get_article(article_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Article)
        .options(
            selectinload(Article.source),
            selectinload(Article.summary),
            selectinload(Article.article_entities).selectinload(ArticleEntity.entity),
        )
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    summary_data = None
    if article.summary:
        summary_data = ArticleSummaryResponse(
            summary=article.summary.summary,
            topics=article.summary.topics,
            key_facts=article.summary.key_facts,
        )

    entities_data = [
        ArticleEntityResponse(
            id=ae.entity.id,
            name=ae.entity.name,
            type=ae.entity.type,
            sentiment=ae.sentiment,
            relevance=ae.relevance,
        )
        for ae in article.article_entities
    ]

    detail = ArticleDetailResponse(
        id=article.id,
        source=ArticleSourceResponse(id=article.source.id, name=article.source.name),
        title=article.title,
        content=article.content,
        author=article.author,
        published_at=article.published_at,
        ingested_at=article.ingested_at,
        analyzed=article.analyzed,
        summary=summary_data,
        entities=entities_data,
    )

    return {"data": detail.model_dump()}


async def _analyze_in_background(article_id: UUID) -> None:
    async with async_session() as session:
        result = await session.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        if article:
            await analyze_article(session, article)


@router.post("/{article_id}/analyze", status_code=202)
async def trigger_analysis(
    article_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    background_tasks.add_task(_analyze_in_background, article_id)
    return {"data": {"message": "Analysis triggered", "article_id": str(article_id)}}
