#!/bin/bash

SINK_BT="snapcast_bt"
SINK_PC="snapcast_pc"
FIFO_SNAPBT="/tmp/snapbtfifo"
FIFO_SNAPPC="/tmp/snappcfifo"

STATE_DIR="/run/bt-snapcast"
NULLSINK_BT_ID_FILE="$STATE_DIR/nullsink_bt.id"
NULLSINK_PC_ID_FILE="$STATE_DIR/nullsink_pc.id"
LOOPBACK_ID_FILE="$STATE_DIR/loopback.id"
LOOPBACK_SOURCE_FILE="$STATE_DIR/loopback.source"
PAREC_BT_PID_FILE="$STATE_DIR/parec_bt.pid"
PAREC_PC_PID_FILE="$STATE_DIR/parec_pc.pid"
DEFAULT_GAIN="120%"
CAPTURE_IDLE_TIMEOUT=60
MONITOR_INTERVAL=2
MPD_CHECK_INTERVAL=5

SNAPCAST_HOST="localhost"
SNAPCAST_PORT="1705"
SNAPCAST_STREAM_MPD="MPD"
SNAPCAST_STREAM_BLUETOOTH="Bluetooth"
SNAPCAST_STREAM_PC="PC"

CURRENT_MODE=""

mkdir -p "$STATE_DIR"

log() {
    echo "[BT-SNAPCAST] $1"
}

snapcast_set_stream() {
    # usage: snapcast_set_stream Bluetooth|PC|MPD
    STREAM_NAME="$1"

    if [ -z "$STREAM_NAME" ]; then
        log "snapcast_set_stream: missing stream name"
        return 1
    fi

    # Get server status
    STATUS_JSON=$(printf '{"id":1,"jsonrpc":"2.0","method":"Server.GetStatus"}\n' \
        | nc "$SNAPCAST_HOST" "$SNAPCAST_PORT")

    # Group IDs are followed by the group's muted flag.  Client IDs are not,
    # so this avoids accidentally selecting a client instead of a group.
    GROUP_IDS=$(printf '%s\n' "$STATUS_JSON" \
        | grep -o '"id":"[^"]*","muted"' \
        | sed 's/^"id":"//; s/","muted"$//')

    if [ -z "$GROUP_IDS" ]; then
        log "snapcast_set_stream: cannot determine group IDs"
        return 2
    fi

    # Switch every group, not only the first/default group.
    while IFS= read -r GROUP_ID; do
        [ -n "$GROUP_ID" ] || continue
        printf '{"id":2,"jsonrpc":"2.0","method":"Group.SetStream","params":{"id":"%s","stream_id":"%s"}}\n' \
            "$GROUP_ID" "$STREAM_NAME" \
            | nc "$SNAPCAST_HOST" "$SNAPCAST_PORT" >/dev/null
        log "switched group $GROUP_ID to $STREAM_NAME"
    done <<EOF
$GROUP_IDS
EOF

    return 0
}

start_bt_audio() {
    BT_SOURCE="$1"

    log "BT CONNECTED: $BT_SOURCE"

    if [ -f "$LOOPBACK_ID_FILE" ]; then
        ACTIVE_SOURCE=$(cat "$LOOPBACK_SOURCE_FILE" 2>/dev/null || true)
        if [ "$ACTIVE_SOURCE" = "$BT_SOURCE" ]; then
            log "Bluetooth loopback already exists"
            return 0
        fi
        stop_bt_audio
    fi

    log "Loading loopback $BT_SOURCE -> $SINK_BT"
    if ! LB_ID=$(pactl load-module module-loopback \
            source="$BT_SOURCE" \
            sink="$SINK_BT" \
            latency_msec=10); then
        log "Could not load Bluetooth loopback for $BT_SOURCE"
        return 1
    fi

    echo "$LB_ID" > "$LOOPBACK_ID_FILE"
    echo "$BT_SOURCE" > "$LOOPBACK_SOURCE_FILE"

    sleep 0.5
    LOOP_SINK_INPUT=$(pactl list sink-inputs short | awk '/module-loopback/ {print $1; exit}')
    if [ -n "$LOOP_SINK_INPUT" ]; then
        log "Setting loopback volume to $DEFAULT_GAIN"
        pactl set-sink-input-volume "$LOOP_SINK_INPUT" "$DEFAULT_GAIN"
    else
        log "Could not find sink input for Bluetooth loopback"
    fi
}

stop_bt_audio() {
    log "BT DISCONNECTED"

    # Keep the sink and FIFO as the permanent Bluetooth Snapcast path. The
    # capture process is stopped separately after the idle timeout.
    if [ -f "$LOOPBACK_ID_FILE" ]; then
        LB_ID=$(cat "$LOOPBACK_ID_FILE")
        log "Unloading loopback module $LB_ID"
        pactl unload-module "$LB_ID"
        rm -f "$LOOPBACK_ID_FILE"
    fi
    rm -f "$LOOPBACK_SOURCE_FILE"
}

start_capture() {
    SINK_NAME="$1"
    FIFO_NAME="$2"
    PAREC_PID_FILE="$3"

    if [ -f "$PAREC_PID_FILE" ] && kill -0 "$(cat "$PAREC_PID_FILE")" 2>/dev/null; then
        return 0
    fi

    log "Starting audio capture for $SINK_NAME"
    parec -d "${SINK_NAME}.monitor" \
          --format=s16le --rate=48000 --channels=2 \
          > "$FIFO_NAME" &
    echo $! > "$PAREC_PID_FILE"
}

stop_capture() {
    SINK_NAME="$1"
    PAREC_PID_FILE="$2"

    if [ ! -f "$PAREC_PID_FILE" ]; then
        return 0
    fi

    PAREC_PID=$(cat "$PAREC_PID_FILE" 2>/dev/null || true)
    if [ -n "$PAREC_PID" ] && kill -0 "$PAREC_PID" 2>/dev/null; then
        log "Stopping idle audio capture for $SINK_NAME after ${CAPTURE_IDLE_TIMEOUT}s"
        kill "$PAREC_PID" 2>/dev/null || true
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            kill -0 "$PAREC_PID" 2>/dev/null || break
            sleep 0.1
        done
        if kill -0 "$PAREC_PID" 2>/dev/null; then
            log "Force-stopping unresponsive audio capture for $SINK_NAME"
            kill -KILL "$PAREC_PID" 2>/dev/null || true
        fi
        wait "$PAREC_PID" 2>/dev/null || true
    fi
    rm -f "$PAREC_PID_FILE"
}

find_bt_source() {
    pactl list short sources | awk '$2 ~ /^bluez_source/ {print $2; exit}'
}

initialize_sink_path() {
    SINK_NAME="$1"
    FIFO_NAME="$2"
    NULLSINK_ID_FILE="$3"
    PAREC_PID_FILE="$4"
    DESCRIPTION="$5"

    if ! pactl list short sinks | awk -v sink_name="$SINK_NAME" \
            '$2 == sink_name {found=1} END {exit !found}'; then
        log "Loading permanent null sink $SINK_NAME"
        NS_ID=$(pactl load-module module-null-sink \
            sink_name="$SINK_NAME" \
            sink_properties="device.description=$DESCRIPTION")
        echo "$NS_ID" > "$NULLSINK_ID_FILE"
    else
        log "Permanent null sink already exists: $SINK_NAME"
    fi

    if [ -e "$FIFO_NAME" ] && [ ! -p "$FIFO_NAME" ]; then
        log "Removing invalid non-FIFO path $FIFO_NAME"
        rm -f "$FIFO_NAME"
    fi
    if [ ! -p "$FIFO_NAME" ]; then
        log "Creating permanent FIFO $FIFO_NAME"
        mkfifo "$FIFO_NAME"
    fi

    # Capture is started lazily by monitor_audio_sources when the source is
    # active. Keeping the sink and FIFO does not require a running parec.
}

initialize_audio_paths() {
    log "Waiting for PulseAudio"
    until pactl info >/dev/null 2>&1; do
        sleep 1
    done

    initialize_sink_path "$SINK_BT" "$FIFO_SNAPBT" "$NULLSINK_BT_ID_FILE" \
        "$PAREC_BT_PID_FILE" "Snapcast_BT"
    initialize_sink_path "$SINK_PC" "$FIFO_SNAPPC" "$NULLSINK_PC_ID_FILE" \
        "$PAREC_PC_PID_FILE" "Snapcast_PC"
}

find_sink_id() {
    pactl list short sinks | awk -v sink_name="$1" '$2 == sink_name {print $1; exit}'
}

pc_audio_active() {
    PC_SINK_ID=$(find_sink_id "$SINK_PC")
    [ -n "$PC_SINK_ID" ] || return 1

    pactl list sink-inputs | awk -v sink_id="$PC_SINK_ID" '
        /^Sink Input #[0-9]+/ {
            if (matched && active) { found=1 }
            matched=0
            active=0
        }
        /^[[:space:]]*Sink: / {
            if ($2 == sink_id) { matched=1 }
        }
        /^[[:space:]]*Corked: no/ {
            if (matched) { active=1 }
        }
        END {
            if (matched && active) { found=1 }
            exit !found
        }
    '
}

bluetooth_audio_active() {
    BT_SINK_ID=$(find_sink_id "$SINK_BT")
    [ -n "$BT_SINK_ID" ] || return 1

    pactl list sink-inputs | awk -v sink_id="$BT_SINK_ID" '
        /^Sink Input #[0-9]+/ {
            if (matched && active) { found=1 }
            matched=0
            active=0
        }
        /^[[:space:]]*Sink: / {
            if ($2 == sink_id) { matched=1 }
        }
        /^[[:space:]]*Corked: no/ {
            if (matched) { active=1 }
        }
        END {
            if (matched && active) { found=1 }
            exit !found
        }
    '
}

mpd_snapcast_active() {
    mpc outputs 2>/dev/null \
        | grep -Eiq '^[[:space:]]*Output [0-9]+ \(snapcast\) is enabled$'
}

set_mode() {
    MODE="$1"
    [ "$MODE" = "$CURRENT_MODE" ] && return 0

    case "$MODE" in
        bluetooth) STREAM_NAME="$SNAPCAST_STREAM_BLUETOOTH" ;;
        pc)        STREAM_NAME="$SNAPCAST_STREAM_PC" ;;
        mpd|none)  STREAM_NAME="$SNAPCAST_STREAM_MPD" ;;
        *)         log "Unknown source mode: $MODE"; return 1 ;;
    esac

    if snapcast_set_stream "$STREAM_NAME"; then
        CURRENT_MODE="$MODE"
        log "active source mode: $MODE"
    fi
}

monitor_audio_sources() {
    PREV_BT=false
    PREV_PC=false
    PREV_MPD=false
    BT_IDLE_SECONDS=0
    PC_IDLE_SECONDS=0
    MPD_ACTIVE=false
    MPD_CHECK_ELAPSED=$MPD_CHECK_INTERVAL

    while :; do
        BT_SOURCE=$(find_bt_source)
        BT_ACTIVE=false
        if [ -n "$BT_SOURCE" ]; then
            BT_ACTIVE=true
            ACTIVE_SOURCE=$(cat "$LOOPBACK_SOURCE_FILE" 2>/dev/null || true)
            if [ ! -f "$LOOPBACK_ID_FILE" ] || [ "$ACTIVE_SOURCE" != "$BT_SOURCE" ]; then
                start_bt_audio "$BT_SOURCE"
            fi
        elif [ -f "$LOOPBACK_ID_FILE" ]; then
            stop_bt_audio
        fi

        PC_ACTIVE=false
        if pc_audio_active; then
            PC_ACTIVE=true
        fi

        BT_AUDIO_ACTIVE=false
        if bluetooth_audio_active; then
            BT_AUDIO_ACTIVE=true
        fi

        if [ "$BT_AUDIO_ACTIVE" = true ]; then
            BT_IDLE_SECONDS=0
            start_capture "$SINK_BT" "$FIFO_SNAPBT" "$PAREC_BT_PID_FILE"
        else
            BT_IDLE_SECONDS=$((BT_IDLE_SECONDS + 1))
            if [ "$BT_IDLE_SECONDS" -ge "$CAPTURE_IDLE_TIMEOUT" ]; then
                stop_capture "$SINK_BT" "$PAREC_BT_PID_FILE"
            fi
        fi

        if [ "$PC_ACTIVE" = true ]; then
            PC_IDLE_SECONDS=0
            start_capture "$SINK_PC" "$FIFO_SNAPPC" "$PAREC_PC_PID_FILE"
        else
            PC_IDLE_SECONDS=$((PC_IDLE_SECONDS + 1))
            if [ "$PC_IDLE_SECONDS" -ge "$CAPTURE_IDLE_TIMEOUT" ]; then
                stop_capture "$SINK_PC" "$PAREC_PC_PID_FILE"
            fi
        fi

        if [ "$MPD_CHECK_ELAPSED" -ge "$MPD_CHECK_INTERVAL" ]; then
            MPD_ACTIVE=false
            if mpd_snapcast_active; then
                MPD_ACTIVE=true
            fi
            MPD_CHECK_ELAPSED=0
        fi

        if [ "$CURRENT_MODE" = "" ]; then
            if [ "$MPD_ACTIVE" = true ]; then
                set_mode mpd
            elif [ "$BT_ACTIVE" = true ]; then
                set_mode bluetooth
            elif [ "$PC_ACTIVE" = true ]; then
                set_mode pc
            else
                set_mode none
            fi
        elif [ "$MPD_ACTIVE" = true ] && [ "$PREV_MPD" = false ]; then
            set_mode mpd
        elif [ "$PC_ACTIVE" = true ] && [ "$PREV_PC" = false ]; then
            set_mode pc
        elif [ "$BT_ACTIVE" = true ] && [ "$PREV_BT" = false ]; then
            set_mode bluetooth
        elif [ "$CURRENT_MODE" = bluetooth ] && [ "$BT_ACTIVE" = false ]; then
            if [ "$PC_ACTIVE" = true ]; then
                set_mode pc
            else
                set_mode mpd
            fi
        fi

        PREV_BT="$BT_ACTIVE"
        PREV_PC="$PC_ACTIVE"
        PREV_MPD="$MPD_ACTIVE"
        sleep "$MONITOR_INTERVAL"
        MPD_CHECK_ELAPSED=$((MPD_CHECK_ELAPSED + MONITOR_INTERVAL))
    done
}

log "BT Snapcast autoplug started"
initialize_audio_paths
monitor_audio_sources

