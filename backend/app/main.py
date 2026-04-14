import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import articles, dashboard, entities, research, sources
from app.database import engine
from app.models import Base
from app.services.analyzer import run_analysis_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running database migrations...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Seed default sources if empty
    from sqlalchemy import func, select

    from app.database import async_session
    from app.models.source import Source

    async with async_session() as session:
        count = (await session.execute(select(func.count(Source.id)))).scalar() or 0
        if count == 0:
            logger.info("Seeding default RSS sources...")
            default_sources = [
                Source(
                    name="Reuters World",
                    url="https://www.reutersagency.com/feed/?best-topics=business-finance",
                    category="finance",
                ),
                Source(
                    name="BBC Business",
                    url="https://feeds.bbci.co.uk/news/business/rss.xml",
                    category="finance",
                ),
                Source(
                    name="The Guardian Business",
                    url="https://www.theguardian.com/uk/business/rss",
                    category="finance",
                ),
                Source(
                    name="CNBC Top News",
                    url="https://search.cnbc.com/rs/search/combinedcms/view.xml"
                    "?partnerId=wrss01&id=100003114",
                    category="finance",
                ),
                Source(
                    name="MarketWatch Top Stories",
                    url="https://feeds.content.dowjones.io/public/rss/mw_topstories",
                    category="finance",
                ),
            ]
            session.add_all(default_sources)
            await session.commit()
            logger.info("Seeded %d sources", len(default_sources))

    analysis_task = asyncio.create_task(run_analysis_loop())
    logger.info("NewsLens backend started")

    yield

    analysis_task.cancel()


app = FastAPI(
    title="NewsLens API",
    description="AI Editorial Intelligence Platform for financial news",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router)
app.include_router(articles.router)
app.include_router(entities.router)
app.include_router(research.router)
app.include_router(dashboard.router)
