.PHONY: up down api migrate migrate-down

up:
	docker compose up -d

down:
	docker compose down

api:
	cd src && uv run uvicorn main:app --reload --port 8000

migrate:
	cd src && uv run python -m db.migrate

migrate-down:
	cd src && uv run python -m db.migrate down
