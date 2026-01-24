#!/bin/sh

DURATION=180   # 3 minuty
INTERVAL=1

SINK=$(pactl info | sed -n 's/^Default Sink: //p')

if [ -z "$SINK" ]; then
    echo "[PA-GEN] No default sink"
    exit 1
fi

ORIG_MUTE=$(pactl get-sink-mute "$SINK" | awk '{print $2}')

restore_mute() {
    echo "[PA_GEN] exiting .. restore default sink"
    pactl set-sink-mute "$SINK" "$ORIG_MUTE" >/dev/null 2>&1 || true
    exit 0
}

trap restore_mute EXIT INT TERM QUIT

echo "[PA-GEN] started (duration=${DURATION}s, mute=$ORIG_MUTE)"

START=$(date +%s)

while true; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))

    if [ "$ELAPSED" -ge "$DURATION" ]; then
        echo "[PA-GEN] time limit reached, exiting"
        break
    fi

    pactl set-sink-mute "$SINK" toggle
    sleep 0.2
    pactl set-sink-mute "$SINK" "$ORIG_MUTE"

    sleep "$INTERVAL"
done

exit 0

