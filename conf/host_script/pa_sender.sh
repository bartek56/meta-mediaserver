#!/bin/bash
#
# PulseRTP-multiroom
#   Loads RTP sender modules to setup multiroom audio at request
#
#   Notes
#     * If you have issues, and have multiple network interfaces, add source_ip= with you prefered local IP
#     * mtu=1408 is good initial value. It makes room for 352 PCM frames in 16/44.1k.
#
pa_rtp_mtu=1408
pa_sink="rtp"

echo "timedatectl status:"
timedatectl status --no-pager | grep 'NTP service: active'
if [[ $? -ne 0 ]]; then
    timedatectl set-ntp true
    sleep 2
    timedatectl status --no-pager | grep 'NTP service: active'
    if [[ $? -ne 0 ]]; then
        echo "WARNING: NTP service not active"
    else
        echo "timedatectl status OK"
    fi
fi

#pactl load-module module-null-sink sink_name=${pa_sink} format=s16be channels=2 rate=44100 sink_properties="device.description='RTP Multicast Sink'"
pactl load-module module-null-sink sink_name=${pa_sink} format=s16be channels=2 rate=44100
pactl load-module module-rtp-send source=${pa_sink}.monitor mtu=${pa_rtp_mtu} destination_ip=192.168.1.5
pactl load-module module-rtp-send source=${pa_sink}.monitor mtu=${pa_rtp_mtu} destination_ip=192.168.1.6

