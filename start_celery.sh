#!/bin/bash
# Script to start Celery worker and beat
# Usage: ./start_celery.sh

cd "$(dirname "$0")"

# Start Celery worker
celery -A utils_site worker --loglevel=info --concurrency=4 &

# Start Celery beat (for periodic tasks)
celery -A utils_site beat --loglevel=info &

echo "Celery worker and beat started"
echo "Worker PID: $!"
echo "Beat PID: $!"
