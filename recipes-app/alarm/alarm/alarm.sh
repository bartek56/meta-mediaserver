#/bin/bash
minVolume=7
maxVolume=65
defaultVolume=9
growingVolume=5
growingSpeed=55
playlist="alarm"
theNewestSongs=false



set -euo pipefail
IFS=$'\n'

prepareMpdToAlarm() {
    mpc stop
    numberOfOutputs=$(mpc outputs | wc -l)
    for i in $(seq 1 $numberOfOutputs); do
        mpc disable ${i}
    done
    mpc enable 1
    mpc --wait clear
    mpc volume $minVolume
    mpc repeat on
    mpc consume off
}


playTheNewestSong() {
    countSongs=0
    lastDays=0
    numberOfSong=$1
    numberOfAllSongs=$((numberOfSong + 4))
    musicDirectoryTemp=$( cat /etc/mpd.conf | grep music_directory | awk '{$1=""}1' )
    musicDirectoryTemp=${musicDirectoryTemp:1}
    musicDirectory="${musicDirectoryTemp//\"}"


    while [ $countSongs -le $numberOfAllSongs ] && [ $lastDays -le 500 ]; do
        lastDays=$((lastDays + 30))
        countSongs=$(find "$musicDirectory" -type f -mtime -"$lastDays" -name "*.mp3" | wc -l)
    done

    musicList=$(find "$musicDirectory" -type f -name "*.mp3" -mtime -"$lastDays" \
| python3 -c '
import sys, os

limit = int(sys.argv[1])
files = []

for line in sys.stdin:
    path = line.strip()
    if path:
        try:
            files.append((os.path.getmtime(path), path))
        except:
            pass

files.sort(reverse=True)

for _, path in files[:limit]:
    print(path)
' "$numberOfAllSongs")

    while IFS= read -r song; do
        [ -n "$song" ] && mpc add "$song"
    done <<< "$musicList"

	mpc random off
    mpc --wait play 1

    # next song on the snooze
    for (( i=0; i<numberOfSong; i++ )); do
        mpc next || break
    done
}


# ----------------------------------------------------------------------------


prepareMpdToAlarm
if [ "$theNewestSongs" == true ]; then
    echo "----- load the newest songs"
    # configParam
    #   snooze - it is snooze alarm
    #   start - first time on the alarm
    configParam=$1
    numberOfSong=0

    if [[ $configParam == "snooze" ]]; then
        if [ -f /tmp/alarmConfig ]; then
            source /tmp/alarmConfig
        fi
        numberOfSong=$((numberOfSong+1))
    fi
    echo "numberOfSong='$numberOfSong'" > /tmp/alarmConfig

    playTheNewestSong $numberOfSong
else
    echo "----- load playlist $playlist"
    mpc --wait load $playlist
    mpc random on
    mpc --wait play
fi

echo "----- start"
status=$(mpc status | head -n1)
if ! mpc status | grep -q "\[playing\]"; then
    echo "----- Nic nie jest odtwarzane, dodaj 10 losowych utworow..."
    mpc listall | shuf -n 10 | mpc add
    mpc random on
    mpc play
fi

# ---------------------- Alarm loop
while :; do

    sleep $growingSpeed

    mpc volume +$growingVolume
    echo ""
    volume=$(mpc volume | grep -o '[0-9]\+')
    if [ "$volume" -ge "$maxVolume" ]; then
        break
    fi
done

# keep max value and then stop alarm
countMaxVolume=1
while [ $countMaxVolume -lt 11 ]; do
    echo "----- MAX VALUE $countMaxVolume"
    sleep $growingSpeed
    countMaxVolume=$((countMaxVolume + 1))
done

echo "----- Auto stop alarm"
systemctl stop alarm_gui.service
mpc stop
exit
