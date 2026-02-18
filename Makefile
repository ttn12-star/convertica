.PHONY: help build up down restart logs shell test migrate collectstatic build-static deploy deploy-prod restart-fast translate-locales

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'For more information, see ci/README.md'

build: ## Build Docker images
	docker compose build

build-prod: ## Build production Docker images
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build

up: ## Start all services
	docker compose up -d

up-prod: ## Start production services
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml up -d

down: ## Stop all services
	docker compose down

restart: ## Fast restart (no static rebuild)
	docker compose restart

restart-prod: ## Fast restart production (no static rebuild)
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml restart

# Static files build (run once after deploy or when static files change)
build-static: ## Build static files (collectstatic + compress + manifest)
	@echo "Building static files..."
	docker compose exec -T web sh -c "\
		python /app/clear_staticfiles.py || true && \
		python manage.py collectstatic --noinput && \
		/app/scripts/compress_static.sh /app/staticfiles || true && \
		python /app/create_manifest.py || true && \
		python manage.py compilemessages || true"
	@echo "Static files built successfully!"

build-static-prod: ## Build static files for production (includes robots.txt)
	@echo "Building static files for production..."
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web sh -c "\
		python /app/clear_staticfiles.py || true && \
		python manage.py collectstatic --noinput && \
		/app/scripts/compress_static.sh /app/staticfiles || true && \
		python /app/ci/generate_robots_txt.py || true && \
		python /app/create_manifest.py || true && \
		python manage.py compilemessages || true"
	@echo "Static files built successfully!"

# Full deploy (build + up + static)
deploy: ## Full deploy: build images, start services, build static
	@echo "Starting full deploy..."
	docker compose build
	docker compose up -d
	@echo "Waiting for services to start..."
	sleep 5
	$(MAKE) build-static
	@echo "Deploy complete!"

deploy-prod: ## Full production deploy: build + up + static
	@echo "Starting production deploy..."
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build
	docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml up -d
	@echo "Waiting for services to start..."
	sleep 5
	$(MAKE) build-static-prod
	@echo "Production deploy complete!"

logs: ## Show logs from all services
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

rebuild: ## Rebuild and restart all services
	docker compose down
	docker compose build --no-cache
	docker compose up -d

# Development tools
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

translate-locales: ## Bulk-translate locale/*/LC_MESSAGES/django.po via l10n-quality
	./scripts/translate_all_locales.sh
