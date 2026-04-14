"""Multi-step AI research agent using Claude's tool-use capability.

Defines tools the agent can call: search_articles, get_entity, get_connections,
get_article_detail. The orchestrator executes them against the database, feeding
results back to Claude until the agent calls synthesize to produce the final output.
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import anthropic
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity, EntityRelationship
from app.models.research import ResearchStep, ResearchTask

logger = logging.getLogger(__name__)

AGENT_TOOLS = [
    {
        "name": "search_articles",
        "description": (
            "Search articles by keyword in title and content. "
            "Returns matching article summaries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keyword or phrase.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return.",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_entity",
        "description": (
            "Look up an entity by name. "
            "Returns the entity details and recent articles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Entity name to look up.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_connections",
        "description": (
            "Get entities connected to a given entity "
            "through co-occurrence in articles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "UUID of the entity.",
                },
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "get_article_detail",
        "description": "Get full article content, summary, and entities for a specific article.",
        "input_schema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "string", "description": "UUID of the article."},
            },
            "required": ["article_id"],
        },
    },
    {
        "name": "synthesize",
        "description": "Produce the final research briefing after investigation is complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "briefing": {"type": "string", "description": "The structured research briefing."},
                "key_findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key findings from the investigation.",
                },
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "article_id": {"type": "string"},
                            "title": {"type": "string"},
                            "relevance": {"type": "string"},
                        },
                    },
                    "description": "Supporting evidence from articles.",
                },
                "follow_up_questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Suggested follow-up research questions.",
                },
            },
            "required": ["briefing", "key_findings", "evidence", "follow_up_questions"],
        },
    },
]


async def _exec_search_articles(session: AsyncSession, query: str, limit: int = 10) -> dict:
    search = f"%{query}%"
    result = await session.execute(
        select(Article)
        .options(selectinload(Article.summary))
        .where(or_(Article.title.ilike(search), Article.content.ilike(search)))
        .order_by(Article.published_at.desc().nullslast())
        .limit(limit)
    )
    articles = result.scalars().all()
    return {
        "article_count": len(articles),
        "articles": [
            {
                "id": str(a.id),
                "title": a.title,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "summary": a.summary.summary if a.summary else None,
            }
            for a in articles
        ],
    }


async def _exec_get_entity(session: AsyncSession, name: str) -> dict:
    result = await session.execute(
        select(Entity).where(Entity.name.ilike(f"%{name}%")).limit(5)
    )
    entities = result.scalars().all()
    if not entities:
        return {"found": False, "message": f"No entity found matching '{name}'"}

    entity = entities[0]
    ae_result = await session.execute(
        select(Article)
        .join(ArticleEntity, ArticleEntity.article_id == Article.id)
        .where(ArticleEntity.entity_id == entity.id)
        .order_by(Article.published_at.desc().nullslast())
        .limit(5)
    )
    articles = ae_result.scalars().all()
    return {
        "found": True,
        "entity": {
            "id": str(entity.id),
            "name": entity.name,
            "type": entity.type,
            "article_count": entity.article_count,
        },
        "recent_articles": [
            {"id": str(a.id), "title": a.title}
            for a in articles
        ],
    }


async def _exec_get_connections(session: AsyncSession, entity_id_str: str) -> dict:
    try:
        entity_id = UUID(entity_id_str)
    except ValueError:
        return {"error": "Invalid UUID"}

    result = await session.execute(
        select(EntityRelationship)
        .where(
            or_(
                EntityRelationship.entity_a_id == entity_id,
                EntityRelationship.entity_b_id == entity_id,
            )
        )
        .order_by(EntityRelationship.strength.desc())
        .limit(20)
    )
    rels = result.scalars().all()

    connected_ids = set()
    for r in rels:
        connected_ids.add(r.entity_a_id if r.entity_b_id == entity_id else r.entity_b_id)

    if not connected_ids:
        return {"connections": []}

    ent_result = await session.execute(
        select(Entity).where(Entity.id.in_(connected_ids))
    )
    entities_map = {e.id: e for e in ent_result.scalars().all()}

    connections = []
    for r in rels:
        other_id = r.entity_a_id if r.entity_b_id == entity_id else r.entity_b_id
        other = entities_map.get(other_id)
        if other:
            connections.append({
                "entity": {"id": str(other.id), "name": other.name, "type": other.type},
                "strength": r.strength,
                "evidence_count": r.evidence_count,
            })

    return {"connections": connections}


async def _exec_get_article_detail(session: AsyncSession, article_id_str: str) -> dict:
    try:
        article_id = UUID(article_id_str)
    except ValueError:
        return {"error": "Invalid UUID"}

    result = await session.execute(
        select(Article)
        .options(
            selectinload(Article.summary),
            selectinload(Article.article_entities)
            .selectinload(ArticleEntity.entity),
        )
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        return {"error": "Article not found"}

    return {
        "id": str(article.id),
        "title": article.title,
        "content": article.content[:3000],
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "summary": article.summary.summary if article.summary else None,
        "entities": [
            {"name": ae.entity.name, "type": ae.entity.type, "sentiment": ae.sentiment}
            for ae in article.article_entities
        ],
    }


TOOL_EXECUTORS = {
    "search_articles": lambda session, inp: _exec_search_articles(
        session, inp["query"], inp.get("limit", 10),
    ),
    "get_entity": lambda session, inp: _exec_get_entity(
        session, inp["name"],
    ),
    "get_connections": lambda session, inp: _exec_get_connections(
        session, inp["entity_id"],
    ),
    "get_article_detail": lambda session, inp: _exec_get_article_detail(
        session, inp["article_id"],
    ),
}

ACTION_MAP = {
    "search_articles": "search_articles",
    "get_entity": "map_entities",
    "get_connections": "discover_connections",
    "get_article_detail": "search_articles",
}


async def record_step(
    session: AsyncSession,
    task_id: UUID,
    step_number: int,
    action: str,
    input_data: dict | None,
    output_data: dict | None,
) -> ResearchStep:
    step = ResearchStep(
        task_id=task_id,
        step_number=step_number,
        action=action,
        input_data=input_data,
        output_data=output_data,
    )
    session.add(step)
    await session.flush()
    return step


async def run_research(
    session: AsyncSession,
    task: ResearchTask,
    client: anthropic.AsyncAnthropic | None = None,
) -> ResearchTask:
    """Execute a multi-step research investigation using Claude with tool use."""
    if client is None:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    task.status = "running"
    await session.flush()

    step_number = 0

    # Step 1: Parse query
    step_number += 1
    await record_step(session, task.id, step_number, "parse_query", {"query": task.query}, None)

    messages = [
        {
            "role": "user",
            "content": (
                f"You are a research agent for a financial news intelligence platform. "
                f"Investigate the following query by searching articles, finding entities, "
                f"discovering connections, and then synthesizing your findings into a briefing.\n\n"
                f"Research query: {task.query}\n\n"
                f"Use the available tools to investigate. When done, call the synthesize tool "
                f"with your findings."
            ),
        }
    ]

    max_iterations = 10
    for _ in range(max_iterations):
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=AGENT_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            # Agent finished without calling synthesize -- extract text as briefing
            text_parts = [b.text for b in response.content if b.type == "text"]
            if text_parts:
                step_number += 1
                result = {
                    "briefing": "\n".join(text_parts),
                    "key_findings": [],
                    "evidence": [],
                    "follow_up_questions": [],
                }
                await record_step(session, task.id, step_number, "synthesize", None, result)
                task.result = result
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            if tool_name == "synthesize":
                step_number += 1
                await record_step(session, task.id, step_number, "synthesize", None, tool_input)
                task.result = tool_input
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Briefing recorded successfully.",
                })
            else:
                executor = TOOL_EXECUTORS.get(tool_name)
                if executor:
                    output = await executor(session, tool_input)
                    step_number += 1
                    action = ACTION_MAP.get(tool_name, tool_name)
                    await record_step(session, task.id, step_number, action, tool_input, output)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(output),
                    })

        if task.result is not None:
            break

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    if task.result is not None:
        task.status = "completed"
    else:
        task.status = "failed"
        task.result = {"error": "Agent did not produce a research briefing"}
    task.completed_at = datetime.now(timezone.utc)
    await session.commit()

    return task
