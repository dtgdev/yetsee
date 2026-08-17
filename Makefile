.PHONY: up down logs test api web

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd apps/api && pytest

api:
	cd apps/api && uvicorn app.main:app --reload --port 8100

web:
	cd apps/web && npm run dev
