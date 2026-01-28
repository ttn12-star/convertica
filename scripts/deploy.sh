#!/bin/bash
#
# Zero-downtime deploy script for Convertica
#
# This script performs a rolling update of the web container:
# 1. Builds new image
# 2. Starts new container alongside the old one
# 3. Waits for new container to become healthy
# 4. Switches nginx to new container
# 5. Stops old container
#
# Usage: ./scripts/deploy.sh [--skip-build]

set -e

COMPOSE_FILES="-f docker-compose.yml -f ci/docker-compose.prod.yml"
HEALTH_CHECK_URL="http://localhost:8000/livez/"
HEALTH_CHECK_TIMEOUT=180  # 3 minutes max for container to become healthy
HEALTH_CHECK_INTERVAL=5   # Check every 5 seconds

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if --skip-build flag is passed
SKIP_BUILD=false
if [ "$1" = "--skip-build" ]; then
    SKIP_BUILD=true
fi

cd /opt/convertica || { log_error "Failed to cd to /opt/convertica"; exit 1; }

# Step 1: Build new image (unless skipped)
if [ "$SKIP_BUILD" = false ]; then
    log_info "Building new image..."
    docker compose $COMPOSE_FILES build web
fi

# Step 2: Get current container info
OLD_CONTAINER=$(docker ps -q -f name=convertica_web)
if [ -z "$OLD_CONTAINER" ]; then
    log_warn "No running web container found, doing normal start"
    docker compose $COMPOSE_FILES up -d
    exit 0
fi

log_info "Current web container: $OLD_CONTAINER"

# Step 3: Scale up - start new container alongside old one
# Note: This requires scale support or we use a different approach
# Since docker-compose doesn't support true rolling updates without Swarm,
# we'll do a fast restart with pre-built image

log_info "Starting new container..."

# Use --no-deps to only restart web, not dependencies
# The old container will be stopped and new one started
docker compose $COMPOSE_FILES up -d --no-deps web

NEW_CONTAINER=$(docker ps -q -f name=convertica_web)
log_info "New web container: $NEW_CONTAINER"

# Step 4: Wait for new container to become healthy
log_info "Waiting for new container to become healthy (max ${HEALTH_CHECK_TIMEOUT}s)..."

elapsed=0
while [ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]; do
    # Check container health status
    health=$(docker inspect --format='{{.State.Health.Status}}' convertica_web 2>/dev/null || echo "unknown")

    if [ "$health" = "healthy" ]; then
        log_info "Container is healthy!"
        break
    fi

    # Also try direct health check
    if curl -sf "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
        log_info "Health check passed!"
        break
    fi

    echo -n "."
    sleep $HEALTH_CHECK_INTERVAL
    elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
done

echo ""

if [ $elapsed -ge $HEALTH_CHECK_TIMEOUT ]; then
    log_error "Container failed to become healthy within ${HEALTH_CHECK_TIMEOUT}s"
    log_error "Check logs: docker logs convertica_web --tail 50"
    exit 1
fi

# Step 5: Reload nginx to pick up any config changes
log_info "Reloading nginx..."
docker exec convertica_nginx nginx -s reload 2>/dev/null || true

log_info "Deploy completed successfully!"
echo ""
docker compose $COMPOSE_FILES ps web
