#/bin/bash
minVolume=7
maxVolume=84
defaultVolume=9
growingVolume=5
growingSpeed=50
playlist="Alarm"
theNewestSongs=false



set -e
IFS=$'\n'

prepareMpdToAlarm() {
    #$(ls /mnt/kingston/media/muzyka/Youtube\ list/  -lRt -1 | grep .mp3 | sort -k6 -r | awk '{for(i=9; i<=NF; ++i) printf "%s ", $i; print ""}' | head -n 10)

    #mpc enable "Local Pulse"
    #mpc disable "Client Pulse"
    #mpc disable "Soundbar"
    numberOfOutputs=$(mpc outputs | wc -l)
    for i in $(seq 1 $numberOfOutputs); do
        mpc disable ${i}
    done
    mpc enable 1
    mpc repeat on
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
    mpc --wait clear
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
    # configParam
    # snooze - it is snooze alarm
    # start - first time on the alarm
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
    mpc clear
    mpc --wait load $playlist
    mpc random on
    mpc play
fi


start=true
echo "start"
sleep $growingSpeed

while true ; do
    result=$(mpc volume)
    IFS=':' read -r -a array <<< "$result"
    volume=${array[1]::-1}
    if [ $(($volume >= $maxVolume)) == 1 ]; then
        start=false
        echo "MAX VALUE"
        sleep $growingSpeed
        sleep $growingSpeed
        sleep $growingSpeed
        systemctl stop alarm_gui.service
        mpc stop
        exit
    fi
    if [ "$start" == true ]; then
        result=$(mpc volume +$growingVolume)
        echo $result
    fi

    sleep $growingSpeed
done
