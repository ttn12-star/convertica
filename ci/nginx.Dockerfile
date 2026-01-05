# Nginx with Brotli support
# Uses fholzer/nginx-brotli which is nginx:alpine + brotli module pre-compiled

FROM fholzer/nginx-brotli:latest

# Install wget for healthcheck (if not present)
RUN apk add --no-cache wget || true

# Healthcheck - check internal health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/health/ || exit 1

EXPOSE 80 443
