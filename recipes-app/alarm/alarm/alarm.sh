#/bin/bash
minVolume=7
maxVolume=65
defaultVolume=9
growingVolume=5
growingSpeed=55
playlist="alarm"
theNewestSongs=false



set -e
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
}

playTheNewestSong() {
    countSongs=0
    lastDays=0
    musicDirectoryTemp=$( cat /etc/mpd.conf | grep music_directory | awk '{$1=""}1' )
    musicDirectoryTemp=${musicDirectoryTemp:1}
    musicDirectory="${musicDirectoryTemp//\"}"

    while [ $countSongs -le 4 ]; do
        lastDays=$((lastDays + 1))
        countSongs=$(find $musicDirectory -type f -mtime -$lastDays -name "*.mp3" | wc -l)
    done

    musicList=$(find $musicDirectory -type f -mtime -$lastDays -name "*.mp3" -exec basename '{}' ';' | head -n 10 )
    songs=()
    for songName in $musicList; do
	    songs+=($songName)
    done

    # revert list
    for ((i=${#songs[@]}-1; i>=0; i-- )); do
        mpc --wait listall | grep ${songs[$i]} | mpc add
    done
	mpc random off
    mpc play 1

    # next song on the snooze
    for (( i=0; i<$1; i++ )) ; {
        mpc next
    }
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
    mpc play
fi

echo "----- start"
status=$(mpc status | head -n1)
if ! mpc status | grep -q "\[playing\]"; then
    echo "----- Nic nie jest odtwarzane, dodaję 10 losowych utworów..."
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

