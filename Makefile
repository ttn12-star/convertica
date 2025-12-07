.PHONY: help build up down restart logs shell test migrate collectstatic

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
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

restart: ## Restart all services
	docker compose restart

logs: ## Show logs from all services
	docker compose logs -f

shell: ## Open Django shell in web container
	docker compose exec web python manage.py shell

test: ## Run tests
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
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build

dev-down: ## Stop development environment
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi all

rebuild: ## Rebuild and restart all services
	docker compose down
	docker compose build --no-cache
	docker compose up -d

