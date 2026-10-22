#!/bin/bash

source /opt/installCommon.sh

configure_serial_gettys()
{
    # if those serial is enable, blutooth not working
    systemctl disable serial-getty@ttyS0.service
    systemctl disable getty@tty1
}

configure_alarm()
{
    chgrp www-data /etc/mediaserver/alarm.ini
    local alarm_unit
    alarm_unit="$(systemctl show --property=FragmentPath --value alarm.timer || true)"
    if [ -n "$alarm_unit" ] && [ -e "$alarm_unit" ]; then
        chgrp www-data "$alarm_unit"
    fi
}

configure_startGUI()
{
    systemctl enable psplash-start.service
    systemctl enable psplash-quit.service
    systemctl enable start.service
    systemctl disable startup.service
}

set -e

configure_vim
configure_serial_gettys
# systemctl enable mysqld.service
disable_dhcpcd
configure_swappiness
configure_alarm
#chgrp www-data /etc/mediaserver/youtubedl.ini
#chown 775 /etc/mediaserver/youtubedl.ini
pactl set-card-profile "alsa_card.hdmi" off

configure_volume
configure_startGUI
