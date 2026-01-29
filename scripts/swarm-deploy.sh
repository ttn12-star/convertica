#!/bin/bash
#
# Docker Swarm deploy script for Convertica
#
# Features:
# - Zero-downtime rolling updates
# - Automatic rollback on failure
# - Health check monitoring
#
# Usage:
#   ./scripts/swarm-deploy.sh init     # Initialize Swarm (one-time)
#   ./scripts/swarm-deploy.sh deploy   # Deploy/update stack
#   ./scripts/swarm-deploy.sh status   # Show stack status
#   ./scripts/swarm-deploy.sh rollback # Rollback to previous version
#   ./scripts/swarm-deploy.sh stop     # Stop stack (keeps Swarm)
#   ./scripts/swarm-deploy.sh leave    # Leave Swarm (back to docker-compose)

set -e

STACK_NAME="convertica"
COMPOSE_FILES="-c docker-compose.yml -c ci/docker-compose.prod.yml -c ci/docker-compose.swarm.yml"

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

cd /opt/convertica || { log_error "Failed to cd to /opt/convertica"; exit 1; }

check_swarm_active() {
    if docker info 2>/dev/null | grep -q "Swarm: active"; then
        return 0
    else
        return 1
    fi
}

cmd_init() {
    log_step "Initializing Docker Swarm..."

    if check_swarm_active; then
        log_warn "Swarm is already initialized"
        docker node ls
        return 0
    fi

    # Stop existing docker-compose containers first
    log_info "Stopping existing docker-compose containers..."
    docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

    # Initialize Swarm
    log_info "Initializing Swarm mode..."
    docker swarm init

    log_info "Swarm initialized successfully!"
    echo ""
    log_info "Now run: ./scripts/swarm-deploy.sh deploy"
}

cmd_deploy() {
    log_step "Deploying stack to Swarm..."

    if ! check_swarm_active; then
        log_error "Swarm is not initialized. Run: ./scripts/swarm-deploy.sh init"
        exit 1
    fi

    # Check if .env exists
    if [ ! -f .env ]; then
        log_error ".env file not found"
        exit 1
    fi

    # Export env vars for docker stack (it doesn't support env_file)
    log_info "Loading environment variables..."
    set -a
    source .env
    set +a

    # Build images first
    log_info "Building images..."
    docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build

    # Deploy stack
    log_info "Deploying stack..."
    docker stack deploy $COMPOSE_FILES --with-registry-auth $STACK_NAME

    log_info "Waiting for services to start..."
    sleep 10

    # Show status
    cmd_status

    log_info "Deploy complete! Services are updating with zero-downtime."
    echo ""
    log_info "Monitor progress: docker service ls"
    log_info "Watch logs: docker service logs -f ${STACK_NAME}_web"
}

cmd_status() {
    log_step "Stack status:"
    echo ""

    if ! check_swarm_active; then
        log_warn "Swarm is not active"
        return 1
    fi

    echo "Services:"
    docker stack services $STACK_NAME 2>/dev/null || log_warn "Stack not deployed"
    echo ""

    echo "Tasks:"
    docker stack ps $STACK_NAME --no-trunc 2>/dev/null | head -20 || true
}

cmd_rollback() {
    log_step "Rolling back services..."

    if ! check_swarm_active; then
        log_error "Swarm is not active"
        exit 1
    fi

    # Rollback web service
    log_info "Rolling back web service..."
    docker service rollback ${STACK_NAME}_web || log_warn "Web rollback failed or nothing to rollback"

    # Rollback celery
    log_info "Rolling back celery service..."
    docker service rollback ${STACK_NAME}_celery || log_warn "Celery rollback failed or nothing to rollback"

    log_info "Rollback initiated. Check status:"
    cmd_status
}

cmd_stop() {
    log_step "Stopping stack..."

    if ! check_swarm_active; then
        log_warn "Swarm is not active"
        return 0
    fi

    docker stack rm $STACK_NAME

    log_info "Stack removed. Swarm is still active."
    log_info "To leave Swarm: ./scripts/swarm-deploy.sh leave"
}

cmd_leave() {
    log_step "Leaving Docker Swarm..."

    if ! check_swarm_active; then
        log_warn "Not in Swarm mode"
        return 0
    fi

    # Remove stack first
    docker stack rm $STACK_NAME 2>/dev/null || true
    sleep 5

    # Leave swarm
    docker swarm leave --force

    log_info "Left Swarm mode. You can now use docker-compose again:"
    log_info "docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml up -d"
}

cmd_logs() {
    service="${2:-web}"
    docker service logs -f "${STACK_NAME}_${service}" --tail 100
}

cmd_help() {
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  init      Initialize Docker Swarm (one-time setup)"
    echo "  deploy    Deploy or update the stack"
    echo "  status    Show stack status"
    echo "  rollback  Rollback services to previous version"
    echo "  stop      Stop and remove the stack"
    echo "  leave     Leave Swarm mode (back to docker-compose)"
    echo "  logs [service]  Follow logs for a service (default: web)"
    echo ""
    echo "Example workflow:"
    echo "  1. $0 init     # One-time: initialize Swarm"
    echo "  2. $0 deploy   # Deploy stack"
    echo "  3. $0 deploy   # Update (zero-downtime)"
    echo "  4. $0 rollback # If something goes wrong"
}

# Main
case "${1:-help}" in
    init)     cmd_init ;;
    deploy)   cmd_deploy ;;
    status)   cmd_status ;;
    rollback) cmd_rollback ;;
    stop)     cmd_stop ;;
    leave)    cmd_leave ;;
    logs)     cmd_logs "$@" ;;
    *)        cmd_help ;;
esac
