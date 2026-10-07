#!/bin/bash

SINK_NAME="snapcast_bt"
FIFO_SNAPBT="/tmp/snapbtfifo"

STATE_DIR="/run/bt-snapcast"
NULLSINK_ID_FILE="$STATE_DIR/nullsink.id"
LOOPBACK_ID_FILE="$STATE_DIR/loopback.id"
PAREC_PID_FILE="$STATE_DIR/parec.pid"
INITIALIZATION_TIMEOUT=3
DEFAULT_GAIN="120%"

SNAPCAST_HOST="localhost"
SNAPCAST_PORT="1705"
SNAPCAST_STREAM_MPD="MPD"
SNAPCAST_STREAM_BLUETOOTH="Bluetooth"

mkdir -p "$STATE_DIR"

log() {
    echo "[BT-SNAPCAST] $1"
}

snapcast_set_stream() {
    # usage: snapcast_set_stream Bluetooth|MPD
    STREAM_NAME="$1"

    if [ -z "$STREAM_NAME" ]; then
        log "snapcast_set_stream: missing stream name"
        return 1
    fi

    # Get server status
    STATUS_JSON=$(printf '{"id":1,"jsonrpc":"2.0","method":"Server.GetStatus"}\n' \
        | nc "$SNAPCAST_HOST" "$SNAPCAST_PORT")

    # Extract group_id (first/default group)
    GROUP_ID=$(echo "$STATUS_JSON" \
        | sed -n 's/.*"groups":\[{"clients".*"id":"\([^"]*\)","muted".*/\1/p')

    if [ -z "$GROUP_ID" ]; then
        log "snapcast_set_stream: cannot determine group_id"
        return 2
    fi

    # Switch stream
    printf '{"id":2,"jsonrpc":"2.0","method":"Group.SetStream","params":{"id":"%s","stream_id":"%s"}}\n' \
        "$GROUP_ID" "$STREAM_NAME" \
        | nc "$SNAPCAST_HOST" "$SNAPCAST_PORT" >/dev/null
    log "switched to $STREAM_NAME"

    return 0
}

start_bt_audio() {
    BT_SOURCE="$1"

    log "BT CONNECTED: $BT_SOURCE"

    # 1. Null sink
    if ! pactl list short sinks | grep -q "^.*\s$SINK_NAME\s"; then
        log "Loading null sink $SINK_NAME"
        NS_ID=$(pactl load-module module-null-sink \
            sink_name=$SINK_NAME \
            sink_properties=device.description=Snapcast_BT)

        echo "$NS_ID" > "$NULLSINK_ID_FILE"
    else
        log "Null sink already exists"
    fi

    # 2. FIFO_SNAPBT
    if [ ! -p "$FIFO_SNAPBT" ]; then
        log "Creating FIFO_SNAPBT $FIFO_SNAPBT"
        mkfifo "$FIFO_SNAPBT"
    fi

    # 3. parec
    if [ ! -f "$PAREC_PID_FILE" ]; then
        log "Starting parec"
        parec -d ${SINK_NAME}.monitor \
              --format=s16le --rate=48000 --channels=2 \
              > "$FIFO_SNAPBT" &

        echo $! > "$PAREC_PID_FILE"
    fi

    # 4. Loopback BT → Snapcast
    if [ ! -f "$LOOPBACK_ID_FILE" ]; then
        log "Loading loopback $BT_SOURCE -> $SINK_NAME"

        LB_ID=$(pactl load-module module-loopback \
            source="$BT_SOURCE" \
            sink=$SINK_NAME \
            latency_msec=10)

        echo "$LB_ID" > "$LOOPBACK_ID_FILE"

        # ---- Ustawiamy domyślny gain ----
        sleep 0.5  # czekamy aż sink-input powstanie
        LOOP_SINK_INPUT=$(pactl list sink-inputs short | awk '/module-loopback/ {print $1; exit}')
        if [ -n "$LOOP_SINK_INPUT" ]; then
            log "Setting loopback volume to $DEFAULT_GAIN"
            pactl set-sink-input-volume "$LOOP_SINK_INPUT" "$DEFAULT_GAIN"
        else
            log "Nie udało się znaleźć sink-input dla loopbacka"
        fi
    fi
}

stop_bt_audio() {
    log "BT DISCONNECTED"

    # 1. Kill parec
    if [ -f "$PAREC_PID_FILE" ]; then
        PAREC_PID=$(cat "$PAREC_PID_FILE")
        log "Stopping parec ($PAREC_PID)"
        kill "$PAREC_PID" 2>/dev/null
        rm -f "$PAREC_PID_FILE"
    fi

    # 2. Unload loopback
    if [ -f "$LOOPBACK_ID_FILE" ]; then
        LB_ID=$(cat "$LOOPBACK_ID_FILE")
        log "Unloading loopback module $LB_ID"
        pactl unload-module "$LB_ID"
        rm -f "$LOOPBACK_ID_FILE"
    fi

    # 3. Unload null sink
    if [ -f "$NULLSINK_ID_FILE" ]; then
        NS_ID=$(cat "$NULLSINK_ID_FILE")
        log "Unloading null sink module $NS_ID"
        pactl unload-module "$NS_ID"
        rm -f "$NULLSINK_ID_FILE"
    fi
}

init() {
    log "Wait for pa signal.."
    systemctl start pa-event-generator.service
    FIFO_INIT=/tmp/pa-watch.fifo
    rm -f "$FIFO_INIT"
    mkfifo "$FIFO_INIT"

    pactl subscribe >"$FIFO_INIT" &
    PACTL_PID=$!

    if read -r -t "$INITIALIZATION_TIMEOUT" line <"$FIFO_INIT"; then
        echo "[PA-WATCH] event OK: $line"
        kill "$PACTL_PID"
        wait "$PACTL_PID" 2>/dev/null
        rm -f "$FIFO_INIT"
        systemctl stop pa-event-generator.service
    else
        echo "[PA-WATCH] NO EVENT → exiting"
        kill "$PACTL_PID"
        wait "$PACTL_PID" 2>/dev/null
        rm -f "$FIFO_INIT"
        exit 1
    fi
}

main_loop() {
    log "BT Snapcast listening Bluetooth clients.."
    pactl subscribe | while read -r line; do

        # interesują nas tylko zdarzenia źródeł
        echo "$line" | grep -q "source" || continue

        # CONNECT
        if echo "$line" | grep -q "new"; then
            sleep 0.5

            pactl list sources short | while read -r ID NAME REST; do
                if echo "$NAME" | grep -q "^bluez_source"; then
                    # jeśli nie mamy aktywnego loopbacka → nowy connect
                    if [ ! -f "$LOOPBACK_ID_FILE" ]; then
                        start_bt_audio "$NAME"
                        snapcast_set_stream "$SNAPCAST_STREAM_BLUETOOTH"
                    fi
                fi
            done
        fi

        # DISCONNECT
        if echo "$line" | grep -q "remove"; then
            stop_bt_audio
            snapcast_set_stream "$SNAPCAST_STREAM_MPD"
        fi
    done
}


log "BT Snapcast autoplug started"
init
main_loop

