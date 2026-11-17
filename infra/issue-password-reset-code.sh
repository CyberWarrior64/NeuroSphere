#!/usr/bin/env bash
set -euo pipefail

username="${1:-}"
if [[ ! "$username" =~ ^[a-z0-9._-]{3,64}$ ]]; then
  printf 'Usage: %s <username>\n' "$0" >&2
  exit 2
fi

recovery_code="$(openssl rand -hex 32)"
token_hash="$(printf '%s' "$recovery_code" | sha256sum | cut -d' ' -f1)"
if [[ ! "$token_hash" =~ ^[a-f0-9]{64}$ ]]; then
  printf 'Could not create a recovery code.\n' >&2
  exit 1
fi

sql="DELETE FROM platform_password_reset_tokens
WHERE expires_at <= UTC_TIMESTAMP()
   OR user_id = (SELECT id FROM platform_users WHERE username = '$username');
INSERT INTO platform_password_reset_tokens (token_hash, user_id, expires_at)
SELECT '$token_hash', id, UTC_TIMESTAMP() + INTERVAL 30 MINUTE
FROM platform_users WHERE username = '$username' AND enabled = TRUE;
SELECT ROW_COUNT();"

inserted="$(printf '%s\n' "$sql" | docker exec -i neurosphere-mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP --host=127.0.0.1 --user=root --batch --skip-column-names "$MYSQL_DATABASE"')"
if [[ "$inserted" != "1" ]]; then
  printf 'No enabled account was found for that username; no code was issued.\n' >&2
  exit 1
fi

printf 'One-time recovery code for %s (expires in 30 minutes):\n%s\n' "$username" "$recovery_code"
