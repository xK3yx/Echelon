from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.career import Career
from app.schemas.career import CareerRead

router = APIRouter(tags=["careers"])


def _active_careers_query():
    """Base query returning only non-deleted, verified careers for public endpoints."""
    return select(Career).where(Career.deleted_at.is_(None), Career.verified.is_(True))


@router.get("/careers", response_model=list[CareerRead])
async def list_careers(db: AsyncSession = Depends(get_db)) -> list[Career]:
    result = await db.execute(_active_careers_query().order_by(Career.name))
    return list(result.scalars().all())


@router.get("/careers/{slug}", response_model=CareerRead)
async def get_career(slug: str, db: AsyncSession = Depends(get_db)) -> Career:
    result = await db.execute(_active_careers_query().where(Career.slug == slug))
    career = result.scalar_one_or_none()
    if career is None:
        raise HTTPException(status_code=404, detail="Career not found")
    return career
