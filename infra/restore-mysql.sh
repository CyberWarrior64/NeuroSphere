#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly CONTAINER="neurosphere-mysql"
readonly MOUNT_ROOT="/mnt/neurosphere"
readonly BACKUP_ROOT="/mnt/neurosphere/backups/mysql"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"

fail() {
    printf 'restore-mysql: %s\n' "$*" >&2
    exit 1
}

[[ $# -eq 1 ]] || fail "usage: $0 /mnt/neurosphere/backups/mysql/neurosphere_<database>_<timestamp>.sql.gz"
command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v mountpoint >/dev/null 2>&1 || fail "mountpoint is required"
command -v gzip >/dev/null 2>&1 || fail "gzip is required"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"
command -v findmnt >/dev/null 2>&1 || fail "findmnt is required"
mountpoint -q "$MOUNT_ROOT" || fail "$MOUNT_ROOT is not mounted"
[[ ! -L "$MOUNT_ROOT/backups" && ! -L "$BACKUP_ROOT" ]] || fail "backup path may not be a symbolic link"
[[ -d "$BACKUP_ROOT" ]] || fail "backup directory is missing"
backup_mount="$(findmnt -n -o TARGET --target "$BACKUP_ROOT" 2>/dev/null)" || fail "could not verify backup filesystem"
[[ "$backup_mount" == "$MOUNT_ROOT" ]] || fail "backup directory is not on $MOUNT_ROOT"
[[ "$(docker inspect --format '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" == "true" ]] \
    || fail "$CONTAINER is not running"

requested_file="$1"
[[ ! -L "$requested_file" ]] || fail "symbolic-link backups are not accepted"
backup_file="$(realpath -e -- "$requested_file")" || fail "backup file does not exist"
case "$backup_file" in
    "$BACKUP_ROOT/"*.sql.gz) ;;
    *) fail "backup must be under $BACKUP_ROOT and end in .sql.gz" ;;
esac
[[ -f "$backup_file" && -r "$backup_file" ]] || fail "backup file is not readable"
checksum_file="$backup_file.sha256"
[[ -f "$checksum_file" && ! -L "$checksum_file" ]] || fail "matching checksum file is missing"
gzip -t -- "$backup_file" || fail "compressed backup failed integrity check"
(
    cd -- "$BACKUP_ROOT"
    sha256sum -c -- "$(basename -- "$checksum_file")"
) || fail "checksum verification failed"

db_name="$(docker exec "$CONTAINER" printenv MYSQL_DATABASE 2>/dev/null)" \
    || fail "could not read database name from container"
[[ "$db_name" =~ ^[A-Za-z0-9_]+$ ]] || fail "database name has unexpected format"
case "$(basename -- "$backup_file")" in
    "neurosphere_""$db_name""_"*.sql.gz) ;;
    *) fail "backup filename does not match configured database" ;;
esac

printf 'This will overwrite database %s using %s.\n' "$db_name" "$backup_file"
printf 'A current-state backup will be created first.\n'
printf 'Type RESTORE %s to continue: ' "$db_name" >/dev/tty
IFS= read -r confirmation </dev/tty
[[ "$confirmation" == "RESTORE $db_name" ]] || fail "confirmation did not match; no restore performed"

"$SCRIPT_DIR/backup-mysql.sh"

set -o pipefail
gzip -dc -- "$backup_file" \
    | docker exec -i "$CONTAINER" sh -eu -c \
        'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysql --host=127.0.0.1 --user=root'

printf 'Restore completed for database %s.\n' "$db_name"
