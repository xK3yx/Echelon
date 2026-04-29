FROM python:3.11-slim

WORKDIR /app

# System dependencies:
#   libmagic1                     — python-magic (resume MIME detection)
#   libcairo2/libpango/...        — WeasyPrint (PDF export)
#   shared-mime-info              — WeasyPrint MIME lookup
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmagic1 \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

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
    "python-multipart>=0.0.9" \
    "pypdf>=4.3.0" \
    "pdfplumber>=0.11.0" \
    "python-docx>=1.1.0" \
    "python-magic>=0.4.27" \
    "slowapi>=0.1.9" \
    "weasyprint>=62.0" \
    "jinja2>=3.1.0" \
    "pytest>=8.0.0" \
    "pytest-asyncio>=0.23.0" \
    "ruff>=0.4.0" \
    "black>=24.0.0"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
