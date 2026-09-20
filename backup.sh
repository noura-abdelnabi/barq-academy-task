#!/bin/bash
set -e

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/postgres_backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Creating PostgreSQL backup..."
docker exec -t postgres pg_dump -U barq_app -d barq_tasks > "$BACKUP_FILE"

cp "$BACKUP_FILE" "${BACKUP_DIR}/latest.sql"

echo "Backup completed successfully: ${BACKUP_FILE}"
