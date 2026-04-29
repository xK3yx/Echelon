import asyncio
import os
import re

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://echelon:echelon@localhost:5432/echelon"
)

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.career import Career  # noqa: E402

_DB_URL = os.environ["DATABASE_URL"]

# Test fixtures use names like "Test Career <hex>", "Quantum Computing
# Researcher <hex>", "AI Ethics Auditor <hex>" — strip them after the
# session so they don't pile up in the shared dev database.
_TEST_NAME_PATTERN = re.compile(r" [0-9a-f]{8}$")


@pytest.fixture
async def engine():
    e = create_async_engine(_DB_URL)
    async with e.begin() as conn:
        # create_all is idempotent: skips tables that already exist
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest.fixture
async def db(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncClient:
    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def pytest_sessionfinish(session, exitstatus):
    """
    Hard-delete any Career rows whose name matches the test fixture suffix
    pattern.  Runs once after the entire pytest session completes, so the
    shared dev database doesn't accumulate "Test Career abc12345" rows on
    every test run.
    """
    async def _cleanup():
        e = create_async_engine(_DB_URL)
        try:
            async with async_sessionmaker(e)() as s:
                rows = await s.execute(select(Career))
                victims = [
                    c.id for c in rows.scalars().all()
                    if _TEST_NAME_PATTERN.search(c.name)
                ]
                if victims:
                    await s.execute(
                        delete(Career).where(Career.id.in_(victims))
                    )
                    await s.commit()
        finally:
            await e.dispose()

    try:
        asyncio.run(_cleanup())
    except Exception as exc:
        # Cleanup is best-effort — never fail the test run because of it
        print(f"[conftest] post-session cleanup failed: {exc}")
