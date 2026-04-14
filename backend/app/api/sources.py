from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceResponse, SourceUpdate

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("")
async def list_sources(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Source).order_by(Source.name))
    sources = result.scalars().all()
    return {
        "data": [SourceResponse.model_validate(s) for s in sources],
        "meta": {"total": len(sources), "limit": len(sources), "offset": 0},
    }


@router.post("", status_code=201)
async def create_source(body: SourceCreate, session: AsyncSession = Depends(get_session)):
    source = Source(name=body.name, url=body.url, category=body.category)
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return {"data": SourceResponse.model_validate(source)}


@router.patch("/{source_id}")
async def update_source(
    source_id: UUID, body: SourceUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(source, field, value)

    await session.commit()
    await session.refresh(source)
    return {"data": SourceResponse.model_validate(source)}


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    session.delete(source)
    await session.commit()
