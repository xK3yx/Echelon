import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://echelon:echelon@localhost:5432/echelon"
)

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

_DB_URL = os.environ["DATABASE_URL"]


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
