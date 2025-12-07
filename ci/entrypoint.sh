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

# Execute the command passed to the container
exec "$@"

