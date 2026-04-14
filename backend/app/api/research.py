import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.database import async_session, get_session
from app.models.research import ResearchTask
from app.schemas.research import (
    ResearchCreate,
    ResearchDetailResponse,
    ResearchStepResponse,
    ResearchTaskResponse,
)
from app.services.research_agent import run_research

router = APIRouter(prefix="/api/research", tags=["research"])


async def _run_research_background(task_id: UUID) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(ResearchTask).where(ResearchTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            try:
                await run_research(session, task)
            except Exception as e:
                task.status = "failed"
                task.result = {"error": str(e)}
                await session.commit()


@router.post("", status_code=201)
async def create_research(
    body: ResearchCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    task = ResearchTask(query=body.query, status="pending")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    background_tasks.add_task(_run_research_background, task.id)

    return {"data": ResearchDetailResponse.model_validate(task).model_dump()}


@router.get("")
async def list_research(
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    count_result = await session.execute(select(func.count(ResearchTask.id)))
    total = count_result.scalar() or 0

    result = await session.execute(
        select(ResearchTask)
        .order_by(ResearchTask.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    tasks = result.scalars().all()

    return {
        "data": [ResearchTaskResponse.model_validate(t).model_dump() for t in tasks],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/{task_id}")
async def get_research(task_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ResearchTask)
        .options(selectinload(ResearchTask.steps))
        .where(ResearchTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    return {"data": ResearchDetailResponse.model_validate(task).model_dump()}


@router.get("/{task_id}/stream")
async def stream_research(task_id: UUID):
    async def event_generator():
        last_step_count = 0
        while True:
            async with async_session() as session:
                result = await session.execute(
                    select(ResearchTask)
                    .options(selectinload(ResearchTask.steps))
                    .where(ResearchTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                if not task:
                    yield {"event": "error", "data": json.dumps({"error": "Task not found"})}
                    return

                current_steps = len(task.steps)
                if current_steps > last_step_count:
                    for step in task.steps[last_step_count:]:
                        yield {
                            "event": "step",
                            "data": json.dumps(
                                ResearchStepResponse.model_validate(step).model_dump(),
                                default=str,
                            ),
                        }
                    last_step_count = current_steps

                if task.status in ("completed", "failed"):
                    yield {
                        "event": "complete",
                        "data": json.dumps(
                            ResearchDetailResponse.model_validate(task).model_dump(),
                            default=str,
                        ),
                    }
                    return

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
