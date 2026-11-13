#!/bin/sh
# Sauvegarde AXIOME : dump PostgreSQL + archive des fichiers (GED), puis suppression des sauvegardes anciennes.
# Variables : PGHOST PGUSER PGDATABASE PGPASSWORD (libpq), STORAGE_DIR (défaut /data/storage),
#             BACKUP_DIR (défaut /backups), RETENTION_JOURS (défaut 14).
# Restauration : voir deploy/LISEZMOI.md
set -eu
DEST="${BACKUP_DIR:-/backups}"; SRC="${STORAGE_DIR:-/data/storage}"; JOURS="${RETENTION_JOURS:-14}"
HORO=$(date +%Y%m%d_%H%M%S)
mkdir -p "$DEST"

pg_dump --format=custom --no-owner --file="$DEST/base_$HORO.dump.tmp"
mv "$DEST/base_$HORO.dump.tmp" "$DEST/base_$HORO.dump"

tar -czf "$DEST/fichiers_$HORO.tar.gz.tmp" -C "$SRC" .
mv "$DEST/fichiers_$HORO.tar.gz.tmp" "$DEST/fichiers_$HORO.tar.gz"

# Rotation
find "$DEST" -name 'base_*.dump' -mtime +"$JOURS" -delete
find "$DEST" -name 'fichiers_*.tar.gz' -mtime +"$JOURS" -delete
echo "$(date -Iseconds) sauvegarde OK : base_$HORO.dump, fichiers_$HORO.tar.gz (rétention ${JOURS} j)"
