FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "alembic>=1.13.0" \
    "asyncpg>=0.29.0" \
    "pydantic>=2.7.0" \
    "pydantic-settings>=2.2.0" \
    "httpx>=0.27.0" \
    "python-dotenv>=1.0.0" \
    "pytest>=8.0.0" \
    "pytest-asyncio>=0.23.0" \
    "ruff>=0.4.0" \
    "black>=24.0.0"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
