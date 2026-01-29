#!/bin/sh
# Docker event monitor - sends Telegram alerts when containers restart/die
# Runs as a separate lightweight container
#
# Smart detection:
# - Ignores normal deploy events (when container restarts quickly after SIGTERM/SIGKILL)
# - Detects OOM kills from docker inspect
# - Logs signal sources and restart history
# - Works with both docker-compose and Swarm
#
# Usage:
#   docker run -d --name docker-monitor \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -e TELEGRAM_BOT_TOKEN=xxx \
#     -e TELEGRAM_CHAT_ID=xxx \
#     alpine sh -c "apk add docker-cli && sh /monitor.sh"

BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID}"
LOG_FILE="${LOG_FILE:-/var/log/docker-monitor.log}"

# Directory for tracking container deaths and history
STATE_DIR="/tmp/docker-monitor"
HISTORY_DIR="$STATE_DIR/history"
mkdir -p "$STATE_DIR" "$HISTORY_DIR"

# How long to wait before alerting (to check if container restarts)
RESTART_GRACE_SECONDS="${RESTART_GRACE_SECONDS:-15}"

# Maximum restarts per hour before alerting about restart loop
MAX_RESTARTS_PER_HOUR="${MAX_RESTARTS_PER_HOUR:-5}"

log() {
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "[$timestamp] $1"
}

send_telegram() {
    message="$1"
    if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
        # Use wget with POST (available in alpine/busybox)
        wget -q -O /dev/null \
            --post-data="chat_id=${CHAT_ID}&text=${message}&parse_mode=HTML&disable_web_page_preview=true" \
            "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" 2>/dev/null || log "WARN: Failed to send Telegram message"
    fi
}

# Get detailed container info including OOM status
get_container_info() {
    container="$1"
    docker inspect "$container" --format='
OOMKilled: {{.State.OOMKilled}}
ExitCode: {{.State.ExitCode}}
Error: {{.State.Error}}
StartedAt: {{.State.StartedAt}}
FinishedAt: {{.State.FinishedAt}}
RestartCount: {{.RestartCount}}
Status: {{.State.Status}}
' 2>/dev/null || echo "Could not inspect container"
}

# Record restart event for restart-loop detection
record_restart() {
    container="$1"
    history_file="$HISTORY_DIR/${container}.restarts"
    now=$(date +%s)
    echo "$now" >> "$history_file"

    # Clean old entries (older than 1 hour)
    hour_ago=$((now - 3600))
    if [ -f "$history_file" ]; then
        tmp_file=$(mktemp)
        while read ts; do
            [ "$ts" -gt "$hour_ago" ] && echo "$ts"
        done < "$history_file" > "$tmp_file"
        mv "$tmp_file" "$history_file"
    fi
}

# Count restarts in last hour
count_restarts() {
    container="$1"
    history_file="$HISTORY_DIR/${container}.restarts"
    if [ -f "$history_file" ]; then
        wc -l < "$history_file" | tr -d ' '
    else
        echo "0"
    fi
}

check_and_alert() {
    container="$1"
    exitcode="$2"
    timestamp="$3"
    state_file="$STATE_DIR/${container}.pending"

    # Check if container has restarted since we marked it as pending
    if docker inspect "$container" --format='{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        # Container is running - this was a deploy/restart
        record_restart "$container"
        restart_count=$(count_restarts "$container")

        log "INFO: $container recovered (exit: $exitcode, restarts/hour: $restart_count)"

        # Check for restart loop
        if [ "$restart_count" -ge "$MAX_RESTARTS_PER_HOUR" ]; then
            message="⚠️ <b>Restart Loop Detected</b>

📦 Container: <code>${container}</code>
🔄 Restarts: ${restart_count} in last hour
🕐 Time: ${timestamp}

Container is restarting too frequently. Check for issues!"

            send_telegram "$message"
            log "WARN: Restart loop detected for $container ($restart_count restarts/hour)"
        fi

        rm -f "$state_file"
        return
    fi

    # Container still not running - this is a real problem
    container_info=$(get_container_info "$container")
    last_logs=$(cat "$state_file" 2>/dev/null | tail -c 1500 || echo "Could not retrieve logs")

    # Check if OOM killed
    is_oom=$(echo "$container_info" | grep "OOMKilled: true" && echo "yes" || echo "no")

    # Determine exit reason
    case "$exitcode" in
        0)   exit_reason="Clean exit" ;;
        1)   exit_reason="Application error" ;;
        137)
            if [ "$is_oom" = "yes" ]; then
                exit_reason="OOM Killed (out of memory)"
            else
                exit_reason="SIGKILL (forced stop or docker kill)"
            fi
            ;;
        139) exit_reason="Segmentation fault (SIGSEGV)" ;;
        143) exit_reason="SIGTERM (graceful shutdown)" ;;
        *)   exit_reason="Exit code: $exitcode" ;;
    esac

    # Get memory stats if available
    memory_info=""
    if [ "$is_oom" = "yes" ]; then
        memory_info="
<b>Memory:</b> Container exceeded memory limit"
    fi

    message="🔴 <b>Container Crashed</b>

📦 Container: <code>${container}</code>
🕐 Time: ${timestamp}
⚠️ Reason: ${exit_reason}
🖥️ Server: convertica.net
${memory_info}
<b>Container Info:</b>
<pre>$(echo "$container_info" | head -6)</pre>

<b>Last logs:</b>
<pre>${last_logs}</pre>

Container did not restart automatically. Check the server!"

    send_telegram "$message"
    log "ALERT: $container crashed (exit: $exitcode - $exit_reason)"
    rm -f "$state_file"
}

# Check Swarm service events (for Swarm mode)
check_swarm_mode() {
    docker info 2>/dev/null | grep -q "Swarm: active"
}

# Monitor Swarm service events
monitor_swarm_services() {
    docker events --filter 'scope=swarm' --filter 'type=service' \
        --format '{{.Action}} {{.Actor.Attributes.name}}' 2>/dev/null | while read action service; do
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        case "$action" in
            update)
                log "INFO: [Swarm] Service $service updated"
                ;;
            remove)
                log "WARN: [Swarm] Service $service removed"
                ;;
        esac
    done
}

log "Starting Docker event monitor..."
log "Bot token configured: $([ -n "$BOT_TOKEN" ] && echo 'yes' || echo 'no')"
log "Chat ID configured: $([ -n "$CHAT_ID" ] && echo 'yes' || echo 'no')"
log "Restart grace period: ${RESTART_GRACE_SECONDS}s"
log "Max restarts per hour: ${MAX_RESTARTS_PER_HOUR}"

if check_swarm_mode; then
    log "Swarm mode detected - monitoring services"
    # Start Swarm service monitor in background
    monitor_swarm_services &
fi

# Listen for docker events with exit code
docker events --filter 'event=die' --filter 'event=start' --filter 'event=oom' --filter 'type=container' \
    --format '{{.Action}} {{.Actor.Attributes.name}} {{.Actor.Attributes.exitCode}}' | while read event container exitcode; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Monitor our project containers (both docker-compose and Swarm naming)
    case "$container" in
        convertica_*|convertica-*)
            case "$event" in
                oom)
                    # OOM event - log immediately
                    log "CRITICAL: $container received OOM signal!"
                    message="🔴 <b>OOM Event</b>

📦 Container: <code>${container}</code>
🕐 Time: ${timestamp}
⚠️ Container is running out of memory!

Check memory limits and application usage."
                    send_telegram "$message"
                    ;;

                die)
                    state_file="$STATE_DIR/${container}.pending"

                    # Exit code 0 or 143 (SIGTERM) are usually intentional stops - just log
                    if [ "$exitcode" = "0" ] || [ "$exitcode" = "143" ]; then
                        log "INFO: $container stopped gracefully (exit: $exitcode)"
                        continue
                    fi

                    # For exit codes 137 (SIGKILL) and others - wait and check if it restarts
                    log "WARN: $container died (exit: $exitcode), waiting ${RESTART_GRACE_SECONDS}s..."

                    # Get detailed container info for logging
                    container_info=$(get_container_info "$container")
                    log "Container info: $(echo "$container_info" | tr '\n' ' ')"

                    # Save logs for potential alert
                    docker logs --tail 20 "$container" 2>&1 > "$state_file" || echo "Could not retrieve logs" > "$state_file"

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
                        log "INFO: $container restarted successfully (deploy/restart detected)"
                        rm -f "$state_file"
                    else
                        log "INFO: $container started"
                    fi
                    ;;
            esac
            ;;
    esac
done
