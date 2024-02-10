#!/bin/bash
idPreviousClient=$(pactl list short modules | grep MediaClients | awk '{print $1}')
if [ -n "${idPreviousClient}" ]; then
    echo "disable active MediaClients ${idPreviousClient}"
    pacmd unload-module ${idPreviousClient}
    sleep 1
fi
devices=$(pacmd list-sinks | grep name | grep tunnel. | awk '{print $2}' | sed 's/<//g' | sed 's/>//g' | sed ':a;N;$!ba;s/\n/,/g')
pacmd load-module module-combine-sink sink_name=MediaClients sink_properties=device.description=MediaClients slaves=$devices
pactl set-default-sink MediaClients
