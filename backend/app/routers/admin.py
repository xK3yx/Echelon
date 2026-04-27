"""
Admin career management endpoints.

All routes require Authorization: Bearer <ADMIN_TOKEN>.
If ADMIN_TOKEN env var is unset the dependency raises 503 before any handler runs.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models.career import Career
from app.schemas.admin import CareerCreate, CareerUpdate
from app.schemas.career import CareerRead

router = APIRouter(
    prefix="/admin/careers",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# ---------------------------------------------------------------------------
# GET /api/admin/careers/proposed
# Must be declared BEFORE /{career_id} routes so FastAPI doesn't swallow it
# ---------------------------------------------------------------------------


@router.get("/proposed", response_model=list[CareerRead])
async def list_proposed_careers(db: AsyncSession = Depends(get_db)) -> list[Career]:
    """List unverified LLM-proposed careers awaiting admin review."""
    result = await db.execute(
        select(Career)
        .where(
            Career.source == "llm_proposed",
            Career.verified.is_(False),
            Career.deleted_at.is_(None),
        )
        .order_by(Career.name)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# POST /api/admin/careers
# ---------------------------------------------------------------------------


@router.post("", response_model=CareerRead, status_code=201)
async def create_career(
    body: CareerCreate,
    db: AsyncSession = Depends(get_db),
) -> Career:
    # Reject duplicate name or slug
    existing = await db.execute(
        select(Career).where(
            (Career.name == body.name) | (Career.slug == body.slug)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="A career with this name or slug already exists.",
        )

    career = Career(
        id=uuid.uuid4(),
        name=body.name,
        slug=body.slug,
        description=body.description,
        required_skills=body.required_skills,
        optional_skills=body.optional_skills,
        personality_fit=body.personality_fit.model_dump(),
        difficulty=body.difficulty,
        growth_potential=body.growth_potential,
        category=body.category,
        source=body.source,
        onet_soc_code=body.onet_soc_code,
        external_url=body.external_url,
        verified=True,
    )
    db.add(career)
    await db.commit()
    await db.refresh(career)
    return career


# ---------------------------------------------------------------------------
# PATCH /api/admin/careers/{career_id}
# ---------------------------------------------------------------------------


@router.patch("/{career_id}", response_model=CareerRead)
async def update_career(
    career_id: uuid.UUID,
    body: CareerUpdate,
    db: AsyncSession = Depends(get_db),
) -> Career:
    result = await db.execute(select(Career).where(Career.id == career_id))
    career = result.scalar_one_or_none()
    if career is None:
        raise HTTPException(status_code=404, detail="Career not found.")

    updates = body.model_dump(exclude_none=True)
    if "personality_fit" in updates:
        updates["personality_fit"] = body.personality_fit.model_dump()  # type: ignore[union-attr]

    for field, value in updates.items():
        setattr(career, field, value)

    await db.commit()
    await db.refresh(career)
    return career


# ---------------------------------------------------------------------------
# DELETE /api/admin/careers/{career_id}  (soft-delete)
# ---------------------------------------------------------------------------


@router.delete("/{career_id}", status_code=204)
async def delete_career(
    career_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Career).where(Career.id == career_id))
    career = result.scalar_one_or_none()
    if career is None:
        raise HTTPException(status_code=404, detail="Career not found.")
    if career.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Career is already deleted.")

    career.deleted_at = datetime.now(UTC)
    await db.commit()


# ---------------------------------------------------------------------------
# POST /api/admin/careers/{career_id}/verify
# ---------------------------------------------------------------------------


@router.post("/{career_id}/verify", response_model=CareerRead)
async def verify_career(
    career_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Career:
    """Promote an llm_proposed career: set verified=True and source='manual'."""
    result = await db.execute(select(Career).where(Career.id == career_id))
    career = result.scalar_one_or_none()
    if career is None:
        raise HTTPException(status_code=404, detail="Career not found.")
    if career.source != "llm_proposed":
        raise HTTPException(
            status_code=409,
            detail="Only llm_proposed careers can be verified via this endpoint.",
        )
    if career.verified:
        raise HTTPException(status_code=409, detail="Career is already verified.")

    career.verified = True
    career.source = "manual"
    await db.commit()
    await db.refresh(career)
    return career
