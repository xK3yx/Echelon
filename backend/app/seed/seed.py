"""Run with: python -m app.seed.seed"""

import asyncio
import json
import logging
import uuid
from pathlib import Path

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.career import Career

logger = logging.getLogger(__name__)


async def seed_careers() -> int:
    careers_file = Path(__file__).parent / "careers.json"
    careers_data: list[dict] = json.loads(careers_file.read_text(encoding="utf-8"))

    inserted = 0
    async with AsyncSessionLocal() as session:
        for entry in careers_data:
            existing = await session.execute(select(Career).where(Career.slug == entry["slug"]))
            if existing.scalar_one_or_none() is not None:
                continue

            session.add(Career(id=uuid.uuid4(), **entry))
            inserted += 1

        await session.commit()

    return inserted


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    count = await seed_careers()
    logger.info("Seeded %d career(s). Skipped duplicates.", count)


if __name__ == "__main__":
    asyncio.run(main())
