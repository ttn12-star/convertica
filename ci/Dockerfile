# syntax=docker/dockerfile:1.4
# Multi-stage build for optimized production image
# Stage 1: Builder
FROM python:3.12-slim AS builder

# Set build arguments
ARG BUILDPLATFORM=linux/amd64
ARG TARGETPLATFORM=linux/amd64

# Install system dependencies for building Python packages
# Split into separate RUN commands for better caching
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install image processing dependencies (cached separately)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install PDF processing dependencies (cached separately)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install LibreOffice (heavy package, cached separately)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-core \
    && rm -rf /var/lib/apt/lists/*

# Install remaining dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install build tools in separate layer for caching
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies - this layer will be cached if requirements.txt doesn't change
# Use pip cache mount for GitHub Actions (works with buildx)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

# Install runtime dependencies (split for better caching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-core \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/staticfiles /app/media /app/logs && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Copy entrypoint script
COPY --chown=appuser:appuser ci/entrypoint.sh /app/entrypoint.sh

# Copy staticfiles clearing script
COPY --chown=appuser:appuser ci/clear_staticfiles.py /app/clear_staticfiles.py
RUN chmod +x /app/clear_staticfiles.py || true

# Create symlink for src module to make it importable from root
# This allows Django to find 'src.frontend' and 'src.blog' apps
RUN ln -s /app/utils_site/src /app/src

# Switch to non-root user
USER appuser

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=utils_site.settings \
    PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "utils_site.wsgi:application"]
