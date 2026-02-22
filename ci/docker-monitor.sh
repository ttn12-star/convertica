#!/bin/sh
# Docker event monitor - sends Telegram alerts when containers restart/die
# Runs as a separate lightweight container

BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID}"

send_telegram() {
    message="$1"
    if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
        # Use wget with POST (available in alpine/busybox)
        wget -q -O /dev/null \
            --post-data="chat_id=${CHAT_ID}&text=${message}&parse_mode=HTML&disable_web_page_preview=true" \
            "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" 2>/dev/null || true
    fi
}

echo "Starting Docker event monitor..."
echo "Bot token configured: $([ -n "$BOT_TOKEN" ] && echo 'yes' || echo 'no')"
echo "Chat ID configured: $([ -n "$CHAT_ID" ] && echo 'yes' || echo 'no')"

# Listen for docker events with exit code
# Note: Using .Action instead of .Status for newer Docker versions
# exitCode is only available for 'die' events, will be empty for 'start'
docker events --filter 'event=die' --filter 'event=start' --filter 'type=container' \
    --format '{{.Action}} {{.Actor.Attributes.name}} {{.Actor.Attributes.exitCode}}' | while read event container exitcode; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')

    # Only alert for our project containers
    case "$container" in
        convertica_*)
            case "$event" in
                die)
                    # Get last 15 lines of logs before container died
                    last_logs=$(docker logs --tail 15 "$container" 2>&1 | head -c 1500 || echo "Could not retrieve logs")

                    # Get extra state details for better diagnostics
                    oom_killed=$(docker inspect --format '{{.State.OOMKilled}}' "$container" 2>/dev/null || echo "unknown")
                    health_status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container" 2>/dev/null || echo "unknown")

                    # Determine exit reason
                    case "$exitcode" in
                        0)   exit_reason="Clean exit" ;;
                        1)   exit_reason="Application error" ;;
                        137)
                            if [ "$oom_killed" = "true" ]; then
                                exit_reason="OOM killed (kernel cgroup OOM)"
                            elif [ "$health_status" = "unhealthy" ]; then
                                exit_reason="SIGKILL by autoheal (container unhealthy)"
                            else
                                exit_reason="SIGKILL (manual kill or orchestrator restart)"
                            fi
                            ;;
                        139) exit_reason="Segmentation fault" ;;
                        143) exit_reason="SIGTERM (graceful shutdown)" ;;
                        *)   exit_reason="Exit code: $exitcode" ;;
                    esac

                    message="🔴 <b>Container Died</b>

📦 Container: <code>${container}</code>
🕐 Time: ${timestamp}
⚠️ Reason: ${exit_reason}
🧠 OOMKilled: ${oom_killed}
❤️ Health: ${health_status}
🖥️ Server: convertica.net

<b>Last logs:</b>
<pre>${last_logs}</pre>

Autoheal should restart it automatically."

                    send_telegram "$message"
                    echo "[$timestamp] ALERT: $container died (exit: $exitcode - $exit_reason)"
                    echo "Last logs:"
                    echo "$last_logs"
                    echo "---"
                    ;;
                start)
                    echo "[$timestamp] INFO: $container started"
                    ;;
            esac
            ;;
    esac
done
