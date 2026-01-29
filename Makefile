.PHONY: help build up down restart logs shell test migrate collectstatic

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Development:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && !/prod/ {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Production (Swarm):'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && /prod|Swarm|Production/ {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'For more information, see ci/README.md'

# =============================================================================
# Development Commands (docker-compose)
# =============================================================================

build: ## Build Docker images (dev)
	docker compose build

up: ## Start all services (dev)
	docker compose up -d

down: ## Stop all services (dev)
	docker compose down

restart: ## Restart all services (dev)
	docker compose restart

logs: ## Show logs from all services (dev)
	docker compose logs -f

shell: ## Open Django shell in web container
	docker compose exec web python manage.py shell

test: ## Run tests
	docker compose exec web python manage.py test --parallel=auto

test-fast: ## Run tests with parallel execution (faster)
	docker compose exec web python manage.py test --parallel=4 --verbosity=1

test-single: ## Run tests without parallelization (for debugging)
	docker compose exec web python manage.py test

migrate: ## Run database migrations
	docker compose exec web python manage.py migrate

collectstatic: ## Collect static files
	docker compose exec web python manage.py collectstatic --noinput

makemigrations: ## Create new migrations
	docker compose exec web python manage.py makemigrations

createsuperuser: ## Create Django superuser
	docker compose exec web python manage.py createsuperuser

dev: ## Start development environment
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-build: ## Build development environment
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache

dev-down: ## Stop development environment
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi all

rebuild: ## Rebuild and restart all services (dev)
	docker compose down
	docker compose build --no-cache
	docker compose up -d

# =============================================================================
# Production Commands (Docker Swarm - zero-downtime)
# =============================================================================

deploy: ## Deploy to production with Swarm (zero-downtime)
	./scripts/deploy.sh

deploy-skip-build: ## Deploy to production without rebuilding images
	./scripts/deploy.sh --skip-build

prod-status: ## Show production Swarm stack status
	./scripts/deploy.sh status

prod-logs: ## Show production logs (web)
	./scripts/deploy.sh logs web

prod-logs-celery: ## Show production celery logs
	./scripts/deploy.sh logs celery

prod-rollback: ## Rollback production to previous version
	./scripts/deploy.sh rollback

prod-stop: ## Stop production stack
	./scripts/deploy.sh stop

# Local Swarm testing (mirrors production)
dev-swarm: ## Start local Swarm stack (test production config)
	@echo "Starting local Swarm stack (mirrors production)..."
	@if ! docker info 2>/dev/null | grep -q "Swarm: active"; then \
		echo "Initializing Swarm..."; \
		docker swarm init 2>/dev/null || docker swarm init --advertise-addr 127.0.0.1; \
	fi
	@set -a && source .env && set +a && \
		docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build && \
		docker stack deploy -c docker-compose.yml -c ci/docker-compose.prod.yml -c ci/docker-compose.swarm.yml --prune convertica
	@echo "Stack deployed. Check status: make dev-swarm-status"

dev-swarm-status: ## Show local Swarm stack status
	docker stack services convertica
	@echo ""
	docker stack ps convertica --no-trunc | head -15

dev-swarm-logs: ## Show local Swarm web logs
	docker service logs -f convertica_web --tail 100

dev-swarm-stop: ## Stop local Swarm stack
	docker stack rm convertica
	@echo "Stack removed. To leave Swarm: docker swarm leave --force"

# Legacy production commands (non-Swarm) - kept for compatibility
build-prod: ## Build production Docker images (non-Swarm)
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build

up-prod: ## Start production services (non-Swarm, use 'make deploy' instead)
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml up -d

# =============================================================================
# Development Tools
# =============================================================================

install-hooks: ## Install pre-commit hooks
	pip install pre-commit
	pre-commit install

lint: ## Run pre-commit on all files
	pre-commit run --all-files

format: ## Format code with black
	black .

check: ## Run all checks (black, ruff)
	black --check .
	ruff check .
