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

install_bootstrap_youtubedl()
{
    printf " ----- Bootstrap for YouTube configuration  ----- \n"
    bootstrapExist=$(ls /opt/youtubedl-web/youtubedlWeb/static| grep bootstrap | wc -l)
    if [ $bootstrapExist -gt 0 ]; then
        printf "Boostrap for youtubedl is installed \n"
    else
        cd /opt/youtubedl-web/youtubedlWeb/static
        wget https://github.com/twbs/bootstrap/releases/download/v5.0.0-beta1/bootstrap-5.0.0-beta1-dist.zip
        unzip bootstrap-5.0.0-beta1-dist.zip
        mv bootstrap-5.0.0-beta1-dist bootstrap-5.0.0 --force
        rm bootstrap-5.0.0-beta1-dist.zip
        # clock picker
        wget https://github.com/weareoutman/clockpicker/archive/gh-pages.zip
        unzip gh-pages.zip
        mv clockpicker-gh-pages clockpicker
        rm gh-pages.zip
    fi
}

install_bootstrap_apache()
{
    printf " ----- Bootstrap for Apache configuration  ----- \n"
    bootstrapExist=$(ls /usr/htdocs/ | grep bootstrap | wc -l)
    if [ $bootstrapExist -gt 0 ]; then
        printf "Boostrap for apache is installed \n"
    else
        cd /usr/htdocs
        wget https://github.com/twbs/bootstrap/releases/download/v5.0.0-beta1/bootstrap-5.0.0-beta1-dist.zip
        unzip bootstrap-5.0.0-beta1-dist.zip
        mv bootstrap-5.0.0-beta1-dist bootstrap-5.0.0 --force
        rm bootstrap-5.0.0-beta1-dist.zip
    fi
}


set -e

install_bootstrap_youtubedl
install_bootstrap_apache
configure_snapweb
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
