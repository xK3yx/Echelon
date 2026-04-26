.PHONY: up down migrate seed test lint

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
