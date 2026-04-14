"""Claude-powered entity extraction from article text.

Uses structured tool output to ensure consistent JSON format for entities.
Handles deduplication by fuzzy-matching against existing entities in the database.
"""

import logging
from uuid import UUID

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.entity import ArticleEntity, Entity

logger = logging.getLogger(__name__)

EXTRACTION_TOOL = {
    "name": "extract_entities",
    "description": (
        "Extract named entities from a news article "
        "with sentiment and relevance scores."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "A 2-3 sentence summary of the article.",
            },
            "topics": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Topic tags for the article "
                    "(e.g., 'mergers & acquisitions', 'oil & gas')."
                ),
            },
            "key_facts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key factual claims made in the article.",
            },
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Canonical name of the entity.",
                        },
                        "type": {
                            "type": "string",
                            "enum": [
                                "person", "company", "location",
                                "topic", "event",
                            ],
                            "description": "The type of entity.",
                        },
                        "sentiment": {
                            "type": "number",
                            "description": (
                                "Sentiment towards this entity, "
                                "from -1.0 (negative) to 1.0 (positive)."
                            ),
                        },
                        "relevance": {
                            "type": "number",
                            "description": (
                                "How relevant this entity is, "
                                "from 0.0 to 1.0."
                            ),
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Brief text snippet showing how the "
                                "entity appears in the article."
                            ),
                        },
                    },
                    "required": [
                        "name", "type", "sentiment",
                        "relevance", "context",
                    ],
                },
                "description": "Named entities found in the article.",
            },
        },
        "required": ["summary", "topics", "key_facts", "entities"],
    },
}


async def extract_entities(
    article_title: str,
    article_content: str,
    client: anthropic.AsyncAnthropic | None = None,
) -> dict:
    """Send article text to Claude for entity extraction using structured tool output."""
    if client is None:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "extract_entities"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Analyze this news article and extract all named entities, a summary, "
                    f"topics, and key facts.\n\n"
                    f"Title: {article_title}\n\n"
                    f"Content:\n{article_content[:8000]}"
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_entities":
            return block.input

    raise ValueError("Claude did not return entity extraction tool output")


def normalize_name(name: str) -> str:
    """Normalize entity name for fuzzy matching."""
    return name.strip().lower().replace(".", "").replace(",", "")


async def resolve_entity(
    session: AsyncSession,
    name: str,
    entity_type: str,
) -> Entity:
    """Find or create an entity, using normalized name matching to avoid duplicates."""
    normalized = normalize_name(name)

    result = await session.execute(
        select(Entity).where(
            func.lower(func.replace(func.replace(Entity.name, ".", ""), ",", "")) == normalized,
            Entity.type == entity_type,
        )
    )
    entity = result.scalar_one_or_none()

    if entity is None:
        entity = Entity(name=name.strip(), type=entity_type)
        session.add(entity)
        await session.flush()

    return entity


async def store_article_entities(
    session: AsyncSession,
    article_id: UUID,
    extraction: dict,
) -> list[ArticleEntity]:
    """Resolve extracted entities against the database and create article-entity associations."""
    article_entities = []

    for raw in extraction.get("entities", []):
        entity = await resolve_entity(session, raw["name"], raw["type"])
        entity.article_count += 1

        ae = ArticleEntity(
            article_id=article_id,
            entity_id=entity.id,
            sentiment=max(-1.0, min(1.0, raw.get("sentiment", 0.0))),
            relevance=max(0.0, min(1.0, raw.get("relevance", 0.5))),
            context=raw.get("context"),
        )
        session.add(ae)
        article_entities.append(ae)

    await session.flush()
    return article_entities
