#!/bin/bash
# Database backup script for Convertica
# Usage: ./scripts/backup_database.sh

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/convertica_backup_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "🔄 Starting database backup..."

# Backup PostgreSQL database
docker compose exec -T db pg_dump -U convertica convertica > "${BACKUP_FILE}"

# Compress backup
gzip "${BACKUP_FILE}"

echo "✅ Database backup completed: ${BACKUP_FILE}.gz"
echo "📊 Backup size: $(du -h ${BACKUP_FILE}.gz | cut -f1)"

# Export operation statistics
echo "📈 Exporting operation statistics..."
docker compose exec web python manage.py operation_stats --days 365 --export

echo "✅ Backup process completed successfully!"
echo ""
echo "Backup location: ${BACKUP_FILE}.gz"
echo "Operation stats: logs/operation_stats/"
