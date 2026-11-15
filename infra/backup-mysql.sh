#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly CONTAINER="neurosphere-mysql"
readonly MOUNT_ROOT="/mnt/neurosphere"
readonly BACKUP_ROOT="/mnt/neurosphere/backups/mysql"

fail() {
    printf 'backup-mysql: %s\n' "$*" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v mountpoint >/dev/null 2>&1 || fail "mountpoint is required"
command -v gzip >/dev/null 2>&1 || fail "gzip is required"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"
command -v findmnt >/dev/null 2>&1 || fail "findmnt is required"
mountpoint -q "$MOUNT_ROOT" || fail "$MOUNT_ROOT is not mounted"
[[ ! -L "$MOUNT_ROOT/backups" && ! -L "$BACKUP_ROOT" ]] || fail "backup path may not be a symbolic link"
[[ "$(docker inspect --format '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" == "true" ]] \
    || fail "$CONTAINER is not running"

db_name="$(docker exec "$CONTAINER" printenv MYSQL_DATABASE 2>/dev/null)" \
    || fail "could not read database name from container"
[[ "$db_name" =~ ^[A-Za-z0-9_]+$ ]] || fail "database name has unexpected format"

install -d -m 0700 "$BACKUP_ROOT"
chmod 0700 "$BACKUP_ROOT"
backup_mount="$(findmnt -n -o TARGET --target "$BACKUP_ROOT" 2>/dev/null)" || fail "could not verify backup filesystem"
[[ "$backup_mount" == "$MOUNT_ROOT" ]] || fail "backup directory is not on $MOUNT_ROOT"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_name="neurosphere_""$db_name""_""$timestamp"".sql.gz"
backup_file="$BACKUP_ROOT/$backup_name"
checksum_file="$backup_file.sha256"
tmp_file="$BACKUP_ROOT/.$backup_name.tmp.$$"
checksum_tmp="$BACKUP_ROOT/.$backup_name.sha256.tmp.$$"
[[ ! -e "$backup_file" && ! -e "$checksum_file" ]] || fail "backup filename already exists"
cleanup() {
    rm -f -- "$tmp_file" "$checksum_tmp"
}
trap cleanup EXIT

docker exec "$CONTAINER" sh -eu -c \
    'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysqldump --host=127.0.0.1 --user=root --single-transaction --routines --triggers --events --hex-blob --databases "$MYSQL_DATABASE"' \
    | gzip -c > "$tmp_file"

[[ -s "$tmp_file" ]] || fail "dump is empty"
gzip -t -- "$tmp_file" || fail "compressed dump failed integrity check"
chmod 0600 "$tmp_file"
mv -- "$tmp_file" "$backup_file"

(
    cd -- "$BACKUP_ROOT"
    sha256sum -- "$backup_name" > "$checksum_tmp"
)
chmod 0600 "$checksum_tmp"
mv -- "$checksum_tmp" "$checksum_file"
trap - EXIT

printf 'Backup: %s\nChecksum: %s\n' "$backup_file" "$checksum_file"
