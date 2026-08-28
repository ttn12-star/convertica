#!/usr/bin/env bash
#
# Server side of the production deploy, called by the "Deploy to server via SSH"
# step in .github/workflows/ci.yml once that step has fetched and reset
# /opt/convertica to the deployed revision — so this file is always the version
# being deployed.
#
# It lives here rather than inline in the YAML because a step input has a hard
# size ceiling (measured at just under 20886 bytes: past it GitHub cannot parse
# the workflow at all, every run dies in 0s, and nothing tells you why). Inline,
# the step sat ~260 bytes short of that, so any added comment broke production
# deploys. Shell belongs in a shell file.
#
# `set -e` is repeated here on purpose: the caller sets it, but this runs as a
# child bash, which does not inherit it, and the rollback paths below depend on
# a non-zero exit propagating.
#
# Inherited from the caller's exported environment: SENTRY_ENVIRONMENT,
# SENTRY_RELEASE, CURRENT_TAG.
# Forwarded by the step's `envs:` input: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID
# (both optional — the cache purge is skipped when unset).
set -e

echo "🔨 Rebuilding containers..."
# Build nginx first (it's a dependency for web)
if ! docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build nginx; then
  echo "⚠️ Nginx build failed, but continuing with other services..."
  echo "   This may be due to network issues pulling base image"
fi
# Build other services
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml build web celery celery-beat

# Rolling deployment with automatic rollback strategy
echo "🔄 Starting rolling deployment with automatic rollback..."
echo "📊 Current memory usage: ~2.1GB limits, server has 2GB RAM + 2GB swap = 4GB total"
echo "✅ Deployment strategy: Sequential (old stops before new starts) - fits in resources"

# Save current container IDs for rollback BEFORE starting new ones
# Note: docker compose up -d will stop and remove old containers, so we save IDs first
# We need to save both running and stopped containers
OLD_WEB_ID=$(docker ps -q -f name=convertica_web | head -1)
if [ -z "$OLD_WEB_ID" ]; then
  # If no running container, check for stopped one
  OLD_WEB_ID=$(docker ps -a -q -f name=convertica_web | head -1)
fi
OLD_CELERY_ID=$(docker ps -q -f name=convertica_celery | head -1)
if [ -z "$OLD_CELERY_ID" ]; then
  OLD_CELERY_ID=$(docker ps -a -q -f name=convertica_celery | head -1)
fi
OLD_CELERY_BEAT_ID=$(docker ps -q -f name=convertica_celery_beat | head -1)
if [ -z "$OLD_CELERY_BEAT_ID" ]; then
  OLD_CELERY_BEAT_ID=$(docker ps -a -q -f name=convertica_celery_beat | head -1)
fi
echo "📋 Saved old container IDs for rollback: web=$OLD_WEB_ID, celery=$OLD_CELERY_ID, beat=$OLD_CELERY_BEAT_ID"

# Step 1: Start new web container and wait for healthcheck
# docker compose up -d will stop old and start new (sequential, not parallel)
echo "📦 Starting new web container (waiting for healthcheck)..."
echo "   Note: Old container will be stopped before new one starts (sequential deployment)"
if ! docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml up -d --no-deps --wait web; then
  echo "❌ Failed to start new web container"
  echo "🔍 Diagnostics (web container)"
  docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml ps web || true
  docker ps -a --filter name=convertica_web --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' || true
  echo "--- docker logs (last 200) ---"
  docker logs --tail 200 convertica_web 2>/dev/null || true
  echo "--- docker inspect (health) ---"
  docker inspect --format='{{json .State.Health}}' convertica_web 2>/dev/null || true
  echo "🔄 Rolling back - restoring old container..."
  if [ -n "$OLD_WEB_ID" ]; then
    echo "   Restoring old web container (ID: $OLD_WEB_ID)..."
    docker start "$OLD_WEB_ID" 2>/dev/null || true
  else
    echo "   ⚠️ No old container found to restore"
  fi
  exit 1
fi

NEW_WEB_ID=$(docker ps -q -f name=convertica_web)

# Wait for container to be fully ready and healthy
echo "⏳ Waiting for web container to be fully ready and healthy..."
max_health_attempts=30
health_attempt=0
container_healthy=false
while [ $health_attempt -lt $max_health_attempts ]; do
  # Check if container is healthy (Docker healthcheck)
  if docker inspect --format='{{.State.Health.Status}}' "$NEW_WEB_ID" 2>/dev/null | grep -q "healthy"; then
    echo "✅ Container is healthy!"
    container_healthy=true
    break
  fi
  health_attempt=$((health_attempt + 1))
  echo "   Waiting for healthcheck... (${health_attempt}/${max_health_attempts})"
  sleep 2
done

if [ "$container_healthy" = false ]; then
  echo "⚠️ Container healthcheck not passed, but continuing with additional wait..."
fi

# Additional wait to ensure Django is fully ready to accept requests
echo "⏳ Additional wait to ensure Django is fully ready..."
sleep 10

# Step 1.5: Backup database and verify data BEFORE migrations
echo "💾 Creating database backup before migrations..."
mkdir -p /opt/convertica/backups
BACKUP_FILE="/opt/convertica/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T db pg_dump -U convertica convertica | gzip > "$BACKUP_FILE" || echo "⚠️ Backup failed (non-critical)"
if [ -f "$BACKUP_FILE" ]; then
  echo "✅ Backup created: $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1))"
fi

# Count data BEFORE migrations
echo "📊 Checking data count before migrations..."
OPERATIONS_BEFORE=$(docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py shell -c "from src.users.models import OperationRun; print(OperationRun.objects.count())" 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
USERS_BEFORE=$(docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py shell -c "from src.users.models import User; print(User.objects.count())" 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
ARTICLES_BEFORE=$(docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py shell -c "from src.blog.models import Article; print(Article.objects.count())" 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
echo "   Operations: $OPERATIONS_BEFORE"
echo "   Users: $USERS_BEFORE"
echo "   Articles: $ARTICLES_BEFORE"

# Step 2: Run migrations (container must be running)
echo "📊 Running migrations..."
max_attempts=5
attempt=0
migration_success=false
while [ $attempt -lt $max_attempts ]; do
  if docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py migrate --noinput; then
    echo "✅ Migrations completed!"
    migration_success=true
    break
  fi
  attempt=$((attempt + 1))
  echo "   Retry ${attempt}/${max_attempts}..."
  sleep 3
done

if [ "$migration_success" = false ]; then
  echo "❌ Migrations failed after ${max_attempts} attempts"
  echo "🔄 Rolling back - stopping new container, restoring old..."
  docker stop "$NEW_WEB_ID" 2>/dev/null || true
  docker rm "$NEW_WEB_ID" 2>/dev/null || true
  if [ -n "$OLD_WEB_ID" ]; then
    echo "   Restoring old web container (ID: $OLD_WEB_ID)..."
    docker start "$OLD_WEB_ID" 2>/dev/null || true
  else
    echo "   ⚠️ No old container found to restore"
  fi
  exit 1
fi

# Step 2.4: Sync subscription plans with the provider ids in the environment.
# The provider product/price ids live in .env, but nothing on the server read
# them: the seed command was only ever run by hand. A freshly configured
# provider therefore left SubscriptionPlan.<provider>_product_id empty and every
# checkout answered 503 with "Plan is not configured", on a deploy that looked
# completely green. The command is idempotent and refuses to blank an id that is
# already set, so running it every deploy is safe and stops env and DB drifting.
echo "💳 Syncing subscription plans with provider ids..."
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web \
  python manage.py create_subscription_plans || echo "⚠️ Plan sync failed (non-critical)"

# Step 2.5: Verify data AFTER migrations (detect data loss)
echo "🔍 Verifying data after migrations..."
OPERATIONS_AFTER=$(docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py shell -c "from src.users.models import OperationRun; print(OperationRun.objects.count())" 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
USERS_AFTER=$(docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py shell -c "from src.users.models import User; print(User.objects.count())" 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
ARTICLES_AFTER=$(docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py shell -c "from src.blog.models import Article; print(Article.objects.count())" 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
echo "   Operations: $OPERATIONS_AFTER (was: $OPERATIONS_BEFORE)"
echo "   Users: $USERS_AFTER (was: $USERS_BEFORE)"
echo "   Articles: $ARTICLES_AFTER (was: $ARTICLES_BEFORE)"

# Check for critical data loss (Users or Articles should never decrease)
if [ "$USERS_AFTER" -lt "$USERS_BEFORE" ] || [ "$ARTICLES_AFTER" -lt "$ARTICLES_BEFORE" ]; then
  echo "❌ CRITICAL: Data loss detected after migrations!"
  echo "   Users: $USERS_BEFORE → $USERS_AFTER"
  echo "   Articles: $ARTICLES_BEFORE → $ARTICLES_AFTER"
  echo "🔄 Rolling back and restoring from backup..."

  # Restore from backup
  if [ -f "$BACKUP_FILE" ]; then
    echo "📦 Restoring database from backup..."
    gunzip -c "$BACKUP_FILE" | docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T db psql -U convertica convertica || echo "⚠️ Restore failed"
  fi

  # Rollback containers
  docker stop "$NEW_WEB_ID" 2>/dev/null || true
  docker rm "$NEW_WEB_ID" 2>/dev/null || true
  if [ -n "$OLD_WEB_ID" ]; then
    echo "   Restoring old web container (ID: $OLD_WEB_ID)..."
    docker start "$OLD_WEB_ID" 2>/dev/null || true
  fi
  exit 1
fi

# Warn if operations decreased significantly (but don't fail)
if [ "$OPERATIONS_BEFORE" -gt 0 ] && [ "$OPERATIONS_AFTER" -lt "$OPERATIONS_BEFORE" ]; then
  echo "⚠️ WARNING: Operations count decreased: $OPERATIONS_BEFORE → $OPERATIONS_AFTER"
  echo "   This might indicate a migration issue or cleanup task"
  echo "   Backup available at: $BACKUP_FILE"
else
  echo "✅ Data verification passed!"
fi

# Step 3: Compile translations (CRITICAL - must succeed)
echo "🌍 Compiling translations..."
if ! docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py compilemessages; then
  echo "❌ Translation compilation failed"
  echo "🔄 Rolling back - stopping new container, restoring old..."
  docker stop "$NEW_WEB_ID" 2>/dev/null || true
  docker rm "$NEW_WEB_ID" 2>/dev/null || true
  if [ -n "$OLD_WEB_ID" ]; then
    echo "   Restoring old web container (ID: $OLD_WEB_ID)..."
    docker start "$OLD_WEB_ID" 2>/dev/null || true
  else
    echo "   ⚠️ No old container found to restore"
  fi
  exit 1
fi

# Step 4: Build Tailwind CSS inside container (before collectstatic)
echo "🎨 Building Tailwind CSS inside container..."
# Install Node.js and npm in container if not present, then build CSS
# Run as root to install packages, but build as appuser to match file ownership
if ! docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T --user root web sh -c "
  if command -v npm > /dev/null 2>&1; then
    echo '   npm found, building CSS...'
    cd /app
    chown -R appuser:appuser /app/static /app/package.json /app/package-lock.json 2>/dev/null || true
    su appuser -s /bin/sh -c 'cd /app && npm ci --silent 2>&1 | grep -v npm\ WARN || npm install --silent 2>&1 | grep -v npm\ WARN || true'
    su appuser -s /bin/sh -c 'cd /app && npm run build:css 2>&1' || echo '⚠️ CSS build failed'
    ls -lh /app/static/css/tailwind.css || echo '⚠️ CSS file not found'
  else
    echo '⚠️ npm not found in container, installing Node.js...'
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq curl > /dev/null 2>&1 || true
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1 || true
    apt-get install -y -qq nodejs > /dev/null 2>&1 || echo '⚠️ Node.js installation failed'
    if command -v npm > /dev/null 2>&1; then
      echo '   npm installed, building CSS...'
      cd /app
      chown -R appuser:appuser /app/static /app/package.json /app/package-lock.json 2>/dev/null || true
      su appuser -s /bin/sh -c 'cd /app && npm ci --silent 2>&1 | grep -v npm\ WARN || npm install --silent 2>&1 | grep -v npm\ WARN || true'
      su appuser -s /bin/sh -c 'cd /app && npm run build:css 2>&1' || echo '⚠️ CSS build failed'
    else
      echo '⚠️ npm still not available, CSS should be in repository'
    fi
  fi
"; then
  echo "⚠️ Tailwind CSS build failed, but continuing with collectstatic..."
fi

# Step 5: Collect static files (compress, generate manifest). No wipe first: see ci/clear_staticfiles.py
echo "📦 Collecting and compressing static files..."
if ! docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web sh -c "\
  python manage.py collectstatic --noinput && \
  /app/scripts/compress_static.sh /app/staticfiles || true && \
  python /app/ci/generate_robots_txt.py || true && \
  python /app/create_manifest.py || true"; then
  echo "❌ Static files collection failed"
  echo "🔄 Rolling back - stopping new container, restoring old..."
  docker stop "$NEW_WEB_ID" 2>/dev/null || true
  docker rm "$NEW_WEB_ID" 2>/dev/null || true
  if [ -n "$OLD_WEB_ID" ]; then
    echo "   Restoring old web container (ID: $OLD_WEB_ID)..."
    docker start "$OLD_WEB_ID" 2>/dev/null || true
  else
    echo "   ⚠️ No old container found to restore"
  fi
  exit 1
fi

# Step 6: Clear Django cache (Redis) to ensure fresh content after deploy.
# Preserve the cookieless unique-visitor HLLs (uv:*) — a plain
# cache.clear() FLUSHDBs them and resets the day's uniques on every deploy.
echo "🗑️ Clearing Django cache (preserving unique-visitor counts)..."
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py clear_cache_preserve_uniques || true

# Step 6.5: Clear Cloudflare cache (optional - requires CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID secrets)
if [ -n "${CLOUDFLARE_API_TOKEN:-}" ] && [ -n "${CLOUDFLARE_ZONE_ID:-}" ]; then
  echo "☁️ Purging Cloudflare cache..."
  curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID:-}/purge_cache" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN:-}" \
    -H "Content-Type: application/json" \
    --data '{"purge_everything":true}' | jq -r '.success' | grep -q 'true' && echo "✅ Cloudflare cache purged!" || echo "⚠️ Cloudflare purge failed (non-critical)"
else
  echo "⏭️ Skipping Cloudflare cache purge (secrets not configured)"
fi

# Step 7: Verify health endpoint responds (critical check)
# Final verification
echo "📊 Final data verification:"
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py shell -c "
from src.users.models import OperationRun, SubscriptionPlan, User
from src.blog.models import Article
print(f'✅ Users: {User.objects.count()}')
print(f'✅ Articles: {Article.objects.count()}')
print(f'✅ Plans: {SubscriptionPlan.objects.count()}')
print(f'📊 Operations: {OperationRun.objects.count()}')
" || echo "⚠️ Final verification failed (non-critical)"

# drop the manifest + inline CSS cached before Step 4/5 rebuilt them
docker restart "$NEW_WEB_ID" >/dev/null 2>&1 || true

echo "🏥 Verifying health endpoint (critical check for rollback)..."
max_attempts=10
attempt=0
health_check_passed=false
while [ $attempt -lt $max_attempts ]; do
  if docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✅ Health check passed!"
    health_check_passed=true
    break
  fi
  attempt=$((attempt + 1))
  echo "   Retry ${attempt}/${max_attempts}..."
  sleep 2
done

if [ "$health_check_passed" = false ]; then
  echo "❌ Health check failed after ${max_attempts} attempts"
  echo "🔄 Rolling back - stopping new container, restoring old..."
  docker stop "$NEW_WEB_ID" 2>/dev/null || true
  docker rm "$NEW_WEB_ID" 2>/dev/null || true
  if [ -n "$OLD_WEB_ID" ]; then
    echo "   Restoring old web container (ID: $OLD_WEB_ID)..."
    docker start "$OLD_WEB_ID" 2>/dev/null || true
  else
    echo "   ⚠️ No old container found to restore"
  fi
  exit 1
fi

# Give web container a moment to fully stabilize
echo "⏸️ Waiting 3 seconds for web container to stabilize..."
sleep 3

# Step 6.7: Import blog articles from YAML (idempotent — safe to run on every deploy)
echo "📝 Importing blog articles from YAML files..."
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T web python manage.py import_blog_articles || echo "⚠️ Blog import failed (non-critical)"

# Step 7: Restart other services (with rollback on failure)
echo "🔄 Restarting background workers..."
if ! docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml up -d --no-deps celery celery-beat; then
  echo "⚠️ Failed to restart celery services, but web is healthy - continuing..."
fi

# Step 8: new nginx.conf. Restart, not `nginx -s reload`: git reset
# gives ci/nginx.conf a fresh inode while the container's bind-mount
# stays on the orphaned one, so SIGHUP is a no-op (hit on prod, the
# container was Up 3 months). Restart re-binds it. ~2-3s of 502s.
echo "🔄 Validating nginx config..."
if ! docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml exec -T nginx nginx -t; then
  echo "❌ nginx config invalid — leaving previous config running"
  exit 1
fi
echo "✅ nginx config valid; restarting container to re-bind mount..."
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml restart nginx

# Step 9: Clean up old stopped containers (only if new ones are healthy)
echo "🧹 Cleaning up old stopped containers..."
# Remove old stopped containers (docker compose may have left them)
docker container prune -f --filter "name=convertica_web" --filter "status=exited" 2>/dev/null || true
docker container prune -f --filter "name=convertica_celery" --filter "status=exited" 2>/dev/null || true
docker container prune -f --filter "name=convertica_celery_beat" --filter "status=exited" 2>/dev/null || true

echo "✅ Deployment completed!"

# OS-level backstop for user-file retention: the in-app cleanup
# (celery-beat, every 30 min) is the primary mechanism; this cron
# survives beat dying so uploaded documents never accumulate
# indefinitely (deletion is promised in the privacy copy).
echo "🧹 Installing async_temp reaper cron (backstop for celery-beat)..."
echo '*/30 * * * * root find /opt/convertica/media/async_temp -mindepth 1 -maxdepth 1 -mmin +180 -exec rm -rf {} + 2>/dev/null' > /etc/cron.d/convertica-async-temp-reaper
chmod 644 /etc/cron.d/convertica-async-temp-reaper

# Clean up old Docker images
echo "🧹 Cleaning up old Docker images..."
docker image prune -f || true

echo "✅ Deployment completed!"
