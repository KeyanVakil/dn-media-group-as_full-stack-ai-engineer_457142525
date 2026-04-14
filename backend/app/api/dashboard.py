from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity
from app.models.research import ResearchTask
from app.models.source import Source

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    articles_total = (await session.execute(select(func.count(Article.id)))).scalar() or 0
    articles_analyzed = (
        await session.execute(
            select(func.count(Article.id)).where(Article.analyzed.is_(True))
        )
    ).scalar() or 0
    entities_total = (await session.execute(select(func.count(Entity.id)))).scalar() or 0
    sources_total = (await session.execute(select(func.count(Source.id)))).scalar() or 0
    research_completed = (
        await session.execute(
            select(func.count(ResearchTask.id)).where(ResearchTask.status == "completed")
        )
    ).scalar() or 0

    return {
        "data": {
            "total_articles": articles_total,
            "total_entities": entities_total,
            "total_sources": sources_total,
            "articles_analyzed": articles_analyzed,
            "research_tasks_completed": research_completed,
        }
    }


@router.get("/trends")
async def get_trends(session: AsyncSession = Depends(get_session)):
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    result = await session.execute(
        select(
            Entity.id,
            Entity.name,
            Entity.type,
            func.count(ArticleEntity.id).label("mention_count"),
            func.avg(ArticleEntity.sentiment).label("sentiment_avg"),
        )
        .join(ArticleEntity, ArticleEntity.entity_id == Entity.id)
        .join(Article, Article.id == ArticleEntity.article_id)
        .where(Article.ingested_at >= seven_days_ago)
        .group_by(Entity.id, Entity.name, Entity.type)
        .order_by(func.count(ArticleEntity.id).desc())
        .limit(20)
    )

    trends = []
    for row in result.all():
        trends.append({
            "entity": {"id": str(row.id), "name": row.name, "type": row.type},
            "mention_count": row.mention_count,
            "sentiment_avg": round(float(row.sentiment_avg or 0), 2),
        })

    return {"data": trends}
