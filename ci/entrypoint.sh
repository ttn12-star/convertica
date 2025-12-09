#!/bin/bash
# Entrypoint script for Docker containers
# Creates symlink for src module if it doesn't exist

set -e

# Create symlink for src module if it doesn't exist
# This is needed for development when code is mounted as volume
if [ ! -L /app/src ] && [ ! -d /app/src ]; then
    echo "Creating symlink /app/src -> /app/utils_site/src"
    ln -sf /app/utils_site/src /app/src
fi

# Ensure log files exist (directory permissions should be set on host)
# This is needed because logs directory is mounted as volume
# Note: We can't chmod here because we run as non-root user (appuser)
if [ -d /app/logs ]; then
    # Create log files if they don't exist (will fail silently if no permissions)
    touch /app/logs/errors.log /app/logs/convertica.log 2>/dev/null || true
fi

# Execute the command passed to the container
exec "$@"
