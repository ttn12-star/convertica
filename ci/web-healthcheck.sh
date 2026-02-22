#!/bin/sh
# Web liveness healthcheck for production.
#
# Fails only on hard liveness problems:
# - TCP listener on :8000 is not reachable
# - Gunicorn worker processes are missing
#
# Also logs /livez HTTP status for diagnostics (does not fail on that alone).

set -eu

HOST="${HEALTHCHECK_HOST:-127.0.0.1}"
PORT="${HEALTHCHECK_PORT:-8000}"
TCP_TIMEOUT="${HEALTHCHECK_TCP_TIMEOUT:-2}"

if ! python -c "import socket; s=socket.create_connection(('${HOST}', ${PORT}), ${TCP_TIMEOUT}); s.close()"; then
  echo "[healthcheck] TCP connect failed: ${HOST}:${PORT}"
  exit 1
fi

gunicorn_proc_count="$(pgrep -fc 'gunicorn --config' || true)"
if [ "${gunicorn_proc_count:-0}" -lt 2 ]; then
  echo "[healthcheck] Gunicorn process count too low: ${gunicorn_proc_count:-0} (expected >=2)"
  ps -eo pid,ppid,cmd | grep -E 'gunicorn|python' | grep -v grep || true
  exit 1
fi

# Best-effort HTTP signal for diagnostics.
# Keep non-fatal to avoid false restarts during short worker saturation windows.
livez_code="$(curl -s -o /dev/null --max-time 2 -w '%{http_code}' "http://${HOST}:${PORT}/livez/" || true)"
case "${livez_code}" in
  200|301|302|307|308) : ;;
  *)
    echo "[healthcheck] /livez/ returned unexpected status: ${livez_code:-n/a}"
    ;;
esac

exit 0
