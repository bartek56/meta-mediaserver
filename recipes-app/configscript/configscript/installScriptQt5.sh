#!/bin/bash

source /opt/installCommon.sh

configure_alarm()
{
    chgrp www-data /etc/mediaserver/alarm.ini
    chgrp www-data /lib/systemd/system/alarm.timer
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
