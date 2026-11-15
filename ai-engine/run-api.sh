#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
TMP_ROOT="${NS_AI_TMPDIR:-/mnt/neurosphere/tmp}"
mkdir -p "$TMP_ROOT"
chmod 700 "$TMP_ROOT"
export TMPDIR="$TMP_ROOT" TMP="$TMP_ROOT" TEMP="$TMP_ROOT"
export JOBLIB_TEMP_FOLDER="$TMP_ROOT"
exec .venv/bin/uvicorn app.main:app --host "${NS_AI_BIND_ADDRESS:-127.0.0.1}" --port "${NS_AI_PORT:-8000}"
