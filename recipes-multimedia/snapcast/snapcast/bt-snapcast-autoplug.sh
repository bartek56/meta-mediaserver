#!/bin/bash

SINK_NAME="snapcast_bt"
FIFO="/tmp/snapbtfifo"

STATE_DIR="/run/bt-snapcast"
NULLSINK_ID_FILE="$STATE_DIR/nullsink.id"
LOOPBACK_ID_FILE="$STATE_DIR/loopback.id"
PAREC_PID_FILE="$STATE_DIR/parec.pid"

mkdir -p "$STATE_DIR"

log() {
    echo "[BT-SNAPCAST] $1"
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

    # 2. FIFO
    if [ ! -p "$FIFO" ]; then
        log "Creating FIFO $FIFO"
        mkfifo "$FIFO"
    fi

    # 3. parec
    if [ ! -f "$PAREC_PID_FILE" ]; then
        log "Starting parec"
        parec -d ${SINK_NAME}.monitor \
              --format=s16le --rate=48000 --channels=2 \
              > "$FIFO" &

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

log "BT Snapcast autoplug started"

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
                fi
            fi
        done
    fi

    # DISCONNECT
    if echo "$line" | grep -q "remove"; then
        stop_bt_audio
    fi

done

