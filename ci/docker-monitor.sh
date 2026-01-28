#!/bin/sh
# Docker event monitor - sends Telegram alerts when containers restart/die
# Runs as a separate lightweight container
#
# Smart detection:
# - Ignores normal deploy events (when container restarts quickly after SIGTERM/SIGKILL)
# - Only alerts for actual crashes or failures

BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID}"

# Directory for tracking container deaths (to detect deploy vs crash)
STATE_DIR="/tmp/docker-monitor"
mkdir -p "$STATE_DIR"

# How long to wait before alerting (to check if container restarts)
RESTART_GRACE_SECONDS=15

send_telegram() {
    message="$1"
    if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
        # Use wget with POST (available in alpine/busybox)
        wget -q -O /dev/null \
            --post-data="chat_id=${CHAT_ID}&text=${message}&parse_mode=HTML&disable_web_page_preview=true" \
            "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" 2>/dev/null || true
    fi
}

check_and_alert() {
    container="$1"
    exitcode="$2"
    timestamp="$3"
    state_file="$STATE_DIR/${container}.pending"

    # Check if container has restarted since we marked it as pending
    if docker inspect "$container" --format='{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        # Container is running - this was a deploy/restart, not a crash
        echo "[$timestamp] INFO: $container recovered - was deploy/restart (exit: $exitcode)"
        rm -f "$state_file"
        return
    fi

    # Container still not running - this is a real problem
    last_logs=$(cat "$state_file" 2>/dev/null | tail -c 1500 || echo "Could not retrieve logs")

    # Determine exit reason
    case "$exitcode" in
        0)   exit_reason="Clean exit" ;;
        1)   exit_reason="Application error" ;;
        137) exit_reason="SIGKILL (OOM or forced stop)" ;;
        139) exit_reason="Segmentation fault" ;;
        143) exit_reason="SIGTERM (graceful shutdown)" ;;
        *)   exit_reason="Exit code: $exitcode" ;;
    esac

    message="🔴 <b>Container Crashed</b>

📦 Container: <code>${container}</code>
🕐 Time: ${timestamp}
⚠️ Reason: ${exit_reason}
🖥️ Server: convertica.net

<b>Last logs:</b>
<pre>${last_logs}</pre>

Container did not restart automatically. Check the server!"

    send_telegram "$message"
    echo "[$timestamp] ALERT: $container crashed and did not restart (exit: $exitcode - $exit_reason)"
    rm -f "$state_file"
}

echo "Starting Docker event monitor..."
echo "Bot token configured: $([ -n "$BOT_TOKEN" ] && echo 'yes' || echo 'no')"
echo "Chat ID configured: $([ -n "$CHAT_ID" ] && echo 'yes' || echo 'no')"
echo "Restart grace period: ${RESTART_GRACE_SECONDS}s"

# Listen for docker events with exit code
docker events --filter 'event=die' --filter 'event=start' --filter 'type=container' \
    --format '{{.Action}} {{.Actor.Attributes.name}} {{.Actor.Attributes.exitCode}}' | while read event container exitcode; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')

    # Only monitor our project containers
    case "$container" in
        convertica_*)
            case "$event" in
                die)
                    state_file="$STATE_DIR/${container}.pending"

                    # Exit code 0 or 143 (SIGTERM) are usually intentional stops - just log
                    if [ "$exitcode" = "0" ] || [ "$exitcode" = "143" ]; then
                        echo "[$timestamp] INFO: $container stopped gracefully (exit: $exitcode)"
                        continue
                    fi

                    # For exit codes 137 (SIGKILL) and others - wait and check if it restarts
                    echo "[$timestamp] WARN: $container died (exit: $exitcode), waiting ${RESTART_GRACE_SECONDS}s to check if it restarts..."

                    # Save logs for potential alert
                    docker logs --tail 15 "$container" 2>&1 > "$state_file" || echo "Could not retrieve logs" > "$state_file"

                    # Schedule a check after grace period (in background)
                    (
                        sleep "$RESTART_GRACE_SECONDS"
                        check_and_alert "$container" "$exitcode" "$timestamp"
                    ) &
                    ;;

                start)
                    state_file="$STATE_DIR/${container}.pending"

                    # If there's a pending alert for this container, cancel it
                    if [ -f "$state_file" ]; then
                        echo "[$timestamp] INFO: $container restarted successfully (deploy detected)"
                        rm -f "$state_file"
                    else
                        echo "[$timestamp] INFO: $container started"
                    fi
                    ;;
            esac
            ;;
    esac
done
