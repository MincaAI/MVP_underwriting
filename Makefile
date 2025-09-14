.PHONY: dev stop logs fmt lint

dev:
	@docker compose up --build

stop:
	@docker compose down -v

logs:
	@docker compose logs -f

fmt:
	@ruff --fix .
	@black .

lint:
	@ruff .
	@mypy services packages || true