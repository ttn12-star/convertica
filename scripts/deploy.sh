#!/bin/bash
#
# Unified deploy script for Convertica
#
# Uses Docker Swarm for zero-downtime rolling updates.
# Auto-initializes Swarm if not already active.
#
# Usage:
#   ./scripts/deploy.sh              # Deploy/update (auto-init Swarm if needed)
#   ./scripts/deploy.sh --skip-build # Deploy without rebuilding images
#   ./scripts/deploy.sh status       # Show stack status
#   ./scripts/deploy.sh rollback     # Rollback to previous version
#   ./scripts/deploy.sh logs [svc]   # Follow logs (default: web)
#   ./scripts/deploy.sh stop         # Stop stack
#
# For migration/manual work, access specific services:
#   docker service exec convertica_web python manage.py migrate

set -e

STACK_NAME="convertica"
COMPOSE_FILES="-c docker-compose.yml -c ci/docker-compose.prod.yml -c ci/docker-compose.swarm.yml"
PROJECT_DIR="${PROJECT_DIR:-/opt/convertica}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

cd "$PROJECT_DIR" || { log_error "Failed to cd to $PROJECT_DIR"; exit 1; }

check_swarm_active() {
    docker info 2>/dev/null | grep -q "Swarm: active"
}

init_swarm() {
    log_step "Initializing Docker Swarm (one-time setup)..."

    # Stop existing docker-compose containers first
    log_info "Stopping existing docker-compose containers..."
    docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

    # Initialize Swarm
    log_info "Initializing Swarm mode..."
    docker swarm init 2>/dev/null || {
        # If init fails, it might be because we need to specify advertise-addr
        local ip=$(hostname -I | awk '{print $1}')
        docker swarm init --advertise-addr "$ip"
    }

    log_info "Swarm initialized successfully!"
}

cmd_deploy() {
    local skip_build=false
    if [ "$1" = "--skip-build" ]; then
        skip_build=true
    fi

    log_step "Deploying Convertica with zero-downtime..."

    # Auto-init Swarm if not active
    if ! check_swarm_active; then
        log_warn "Swarm not active, initializing..."
        init_swarm
    fi

    # Check if .env exists
    if [ ! -f .env ]; then
        log_error ".env file not found"
        exit 1
    fi

    # Export env vars for docker stack (it doesn't support env_file)
    log_info "Loading environment variables..."
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a

    # Build images (unless skipped)
    if [ "$skip_build" = false ]; then
        log_info "Building images..."
        docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build
    else
        log_info "Skipping build (--skip-build)"
    fi

    # Generate Swarm-compatible config (removes unsupported options)
    log_info "Generating Swarm-compatible config..."
    MERGED_CONFIG="/tmp/swarm-merged-${STACK_NAME}.yml"
    docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml -f ci/docker-compose.swarm.yml config 2>/dev/null | \
        python3 scripts/swarm-config-converter.py > "$MERGED_CONFIG"

    # Deploy stack with rolling update
    log_info "Deploying stack with rolling update..."
    docker stack deploy -c "$MERGED_CONFIG" --prune $STACK_NAME

    # Wait for services to converge
    log_info "Waiting for services to update..."
    local max_wait=300  # 5 minutes
    local waited=0
    local interval=10

    while [ $waited -lt $max_wait ]; do
        # Check if all services are converged
        local updating=$(docker stack services $STACK_NAME --format '{{.Replicas}}' 2>/dev/null | grep -v "1/1" | wc -l)
        if [ "$updating" -eq 0 ]; then
            log_info "All services converged!"
            break
        fi
        echo -n "."
        sleep $interval
        waited=$((waited + interval))
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        log_warn "Timeout waiting for services to converge. Check status:"
        cmd_status
        exit 1
    fi

    # Run migrations (inside web container)
    log_info "Running migrations..."
    # Wait a bit for container to be ready
    sleep 5
    local web_container=$(docker ps -q -f name="${STACK_NAME}_web" | head -1)
    if [ -n "$web_container" ]; then
        docker exec "$web_container" python manage.py migrate --noinput || log_warn "Migration failed (may be ok if no changes)"
    else
        log_warn "Web container not found for migrations"
    fi

    # Show final status
    echo ""
    cmd_status

    log_info "Deploy complete! Zero-downtime rolling update finished."
    echo ""
    log_info "Useful commands:"
    echo "  - Status:   ./scripts/deploy.sh status"
    echo "  - Logs:     ./scripts/deploy.sh logs web"
    echo "  - Rollback: ./scripts/deploy.sh rollback"
}

cmd_status() {
    log_step "Stack status:"
    echo ""

    if ! check_swarm_active; then
        log_warn "Swarm is not active"
        echo "Using docker-compose status instead:"
        docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml ps
        return 1
    fi

    echo "Services:"
    docker stack services $STACK_NAME 2>/dev/null || log_warn "Stack not deployed"
    echo ""

    echo "Tasks (recent):"
    docker stack ps $STACK_NAME --no-trunc 2>/dev/null | head -15 || true
}

cmd_rollback() {
    log_step "Rolling back services to previous version..."

    if ! check_swarm_active; then
        log_error "Swarm is not active. Cannot rollback."
        exit 1
    fi

    # Rollback web service (most critical)
    log_info "Rolling back web service..."
    docker service rollback "${STACK_NAME}_web" || log_warn "Web rollback failed or nothing to rollback"

    # Rollback celery
    log_info "Rolling back celery service..."
    docker service rollback "${STACK_NAME}_celery" || log_warn "Celery rollback failed"

    # Rollback celery-beat
    log_info "Rolling back celery-beat service..."
    docker service rollback "${STACK_NAME}_celery-beat" || log_warn "Celery-beat rollback failed"

    log_info "Rollback complete. Check status:"
    cmd_status
}

cmd_logs() {
    local service="${1:-web}"
    if check_swarm_active; then
        docker service logs -f "${STACK_NAME}_${service}" --tail 100
    else
        docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml logs -f "$service" --tail 100
    fi
}

cmd_stop() {
    log_step "Stopping stack..."

    if check_swarm_active; then
        docker stack rm $STACK_NAME
        log_info "Stack removed. Swarm is still active."
        log_info "To fully stop Swarm: docker swarm leave --force"
    else
        docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml down
        log_info "Containers stopped."
    fi
}

cmd_help() {
    echo "Convertica Deploy Script (Docker Swarm)"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  (default)     Deploy or update the stack (auto-init Swarm if needed)"
    echo "  --skip-build  Deploy without rebuilding images"
    echo "  status        Show stack status"
    echo "  rollback      Rollback services to previous version"
    echo "  logs [svc]    Follow logs for a service (default: web)"
    echo "  stop          Stop and remove the stack"
    echo "  help          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0              # Build and deploy"
    echo "  $0 --skip-build # Deploy with existing images"
    echo "  $0 status       # Check status"
    echo "  $0 rollback     # Rollback on failure"
    echo "  $0 logs celery  # Follow celery logs"
}

# Main
case "${1:-deploy}" in
    --skip-build) cmd_deploy --skip-build ;;
    status)       cmd_status ;;
    rollback)     cmd_rollback ;;
    logs)         cmd_logs "$2" ;;
    stop)         cmd_stop ;;
    help|--help)  cmd_help ;;
    deploy|*)
        if [ "$1" = "deploy" ]; then
            cmd_deploy "$2"
        else
            cmd_deploy "$1"
        fi
        ;;
esac
