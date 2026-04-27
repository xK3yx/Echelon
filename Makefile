.PHONY: up down migrate seed test lint ingest-onet

up:
	docker compose up --build -d

down:
	docker compose down

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.seed.seed

test:
	docker compose exec backend pytest tests/ -v

lint:
	docker compose exec backend ruff check app/ && docker compose exec backend black --check app/

# Usage: make ingest-onet ONET_DIR=/path/to/extracted/onet/db_XX_X_text
# The directory must contain: Occupation Data.txt, Skills.txt,
# Work Styles.txt, Job Zones.txt
# Data dir is also accessible inside the container at /data/onet if you
# place it at ./data/onet relative to the repo root.
ONET_DIR ?= /data/onet
ingest-onet:
	docker compose exec backend python scripts/ingest_onet.py --data-dir "$(ONET_DIR)"
