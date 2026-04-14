"""Article analysis orchestration.

Picks up unanalyzed articles and processes them through entity extraction,
summary generation, and relationship graph building.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.config import settings
from app.database import async_session
from app.models.article import Article, ArticleSummary
from app.services.entity_extractor import extract_entities, store_article_entities
from app.services.graph_builder import update_relationships

logger = logging.getLogger(__name__)


async def analyze_article(session: AsyncSession, article: Article) -> bool:
    """Analyze a single article: extract entities, create summary, build relationships."""
    try:
        extraction = await extract_entities(article.title, article.content)

        summary = ArticleSummary(
            article_id=article.id,
            summary=extraction.get("summary", ""),
            topics=extraction.get("topics", []),
            key_facts=extraction.get("key_facts", []),
        )
        session.add(summary)

        article_entities = await store_article_entities(
            session, article.id, extraction
        )

        entity_ids = [ae.entity_id for ae in article_entities]
        await update_relationships(session, entity_ids)

        article.analyzed = True
        article.analyzed_at = func.now()
        await session.commit()

        logger.info("Analyzed article: %s", article.title)
        return True

    except Exception:
        logger.exception("Failed to analyze article %s", article.id)
        await session.rollback()
        return False


async def analyze_pending_batch() -> int:
    """Find and analyze a batch of unanalyzed articles. Returns count analyzed."""
    async with async_session() as session:
        result = await session.execute(
            select(Article)
            .where(Article.analyzed.is_(False))
            .order_by(Article.ingested_at)
            .limit(settings.analysis_batch_size)
        )
        articles = result.scalars().all()

        if not articles:
            return 0

        count = 0
        for article in articles:
            if await analyze_article(session, article):
                count += 1

        return count


async def run_analysis_loop() -> None:
    """Background loop that continuously analyzes pending articles."""
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set -- analysis loop disabled")
        return

    logger.info("Starting analysis background loop")
    while True:
        try:
            count = await analyze_pending_batch()
            if count > 0:
                logger.info("Analyzed %d articles in this batch", count)
        except Exception:
            logger.exception("Error in analysis loop")

        await asyncio.sleep(settings.analysis_interval_seconds)
