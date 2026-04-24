.PHONY: help up down restart logs shell ps \
        migrate makemigrations superuser seed \
        test test-backend test-frontend \
        lint lint-backend lint-frontend \
        frontend-install frontend-dev \
        sync-prod-db reset-db clean

COMPOSE := podman-compose -f backend/docker-compose.local.yml
DJANGO_EXEC := $(COMPOSE) exec django

help:
	@echo "BunkLogs development commands"
	@echo ""
	@echo "Container lifecycle:"
	@echo "  make up              Start all containers (django, postgres, redis, mailpit)"
	@echo "  make down            Stop and remove containers"
	@echo "  make restart         Restart the django container"
	@echo "  make logs            Tail django logs (Ctrl+C to exit)"
	@echo "  make ps              Show container status"
	@echo ""
	@echo "Django:"
	@echo "  make migrate         Run pending migrations"
	@echo "  make makemigrations  Generate new migrations"
	@echo "  make superuser       Create Django superuser"
	@echo "  make seed            Seed local DB with synthetic test data (--reset)"
	@echo "  make shell           Open Django shell (shell_plus if available)"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-install  npm install"
	@echo "  make frontend-dev      npm run dev (starts Vite on :5173)"
	@echo ""
	@echo "Quality:"
	@echo "  make test            Run backend + frontend tests"
	@echo "  make lint            Lint backend + frontend"
	@echo ""
	@echo "Database:"
	@echo "  make sync-prod-db    Sync local DB from production (see sync-prod-db.sh)"
	@echo "  make reset-db        Drop local DB volume and re-run migrations"

up:
	$(COMPOSE) up -d
	@echo "Services:"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173 (run 'make frontend-dev' separately)"
	@echo "  Mailpit:  http://localhost:8025"
	@echo "  Admin:    http://localhost:8000/admin/"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart django

logs:
	$(COMPOSE) logs -f django

ps:
	$(COMPOSE) ps

migrate:
	$(DJANGO_EXEC) python manage.py migrate

makemigrations:
	$(DJANGO_EXEC) python manage.py makemigrations

superuser:
	$(DJANGO_EXEC) python manage.py createsuperuser

seed:
	$(DJANGO_EXEC) python manage.py seed_dev_data --reset

shell:
	$(DJANGO_EXEC) python manage.py shell_plus 2>/dev/null || $(DJANGO_EXEC) python manage.py shell

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	$(DJANGO_EXEC) pytest

test-frontend:
	cd frontend && npm run test

lint: lint-backend lint-frontend

lint-backend:
	$(DJANGO_EXEC) ruff check .

lint-frontend:
	@echo "Frontend lint is not configured (no eslint config present)"

sync-prod-db:
	./sync-prod-db.sh

reset-db:
	$(COMPOSE) down -v
	$(COMPOSE) up -d
	@echo "Waiting for postgres to be ready..."
	@sleep 5
	$(DJANGO_EXEC) python manage.py migrate

clean: down
	podman volume rm backend_postgres_data backend_postgres_data_backups 2>/dev/null || true
