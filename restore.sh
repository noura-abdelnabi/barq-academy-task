#!/bin/bash
set -e

BACKUP_FILE=${1:-"backups/latest.sql"}

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file $BACKUP_FILE not found!"
    exit 1
fi

echo "Restoring PostgreSQL database from $BACKUP_FILE..."
cat "$BACKUP_FILE" | docker exec -i postgres psql -U barq_app -d barq_tasks

echo "Database restoration completed successfully!"
