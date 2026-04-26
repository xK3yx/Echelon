from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.career import Career
from app.schemas.career import CareerRead

router = APIRouter(tags=["careers"])


@router.get("/careers", response_model=list[CareerRead])
async def list_careers(db: AsyncSession = Depends(get_db)) -> list[Career]:
    result = await db.execute(select(Career).order_by(Career.name))
    return list(result.scalars().all())


@router.get("/careers/{slug}", response_model=CareerRead)
async def get_career(slug: str, db: AsyncSession = Depends(get_db)) -> Career:
    result = await db.execute(select(Career).where(Career.slug == slug))
    career = result.scalar_one_or_none()
    if career is None:
        raise HTTPException(status_code=404, detail="Career not found")
    return career
