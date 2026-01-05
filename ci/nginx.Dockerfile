# Nginx with Brotli support
# Uses fholzer/nginx-brotli which is nginx:alpine + brotli module pre-compiled

FROM fholzer/nginx-brotli:latest

# Install wget for healthcheck (nginx:alpine usually has it, but ensure it's available)
RUN apk add --no-cache wget || true

# Note: Healthcheck is defined in docker-compose.yml, not here
# This avoids conflicts and allows better control over healthcheck behavior

EXPOSE 80 443
