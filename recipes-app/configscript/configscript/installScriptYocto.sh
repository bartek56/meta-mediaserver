#!/bin/bash

configure_vsftpd()
{
    printf " ----- vsftpd configuration  ----- \n\n"
    adduser -h /home/vsftpd -G nogroup -D -s /bin/false vsftpd
}

configure_minidlna()
{
    printf " ----- MiniDLNA configuration  ----- \n\n"
    systemctl stop minidlna.service
    systemctl disable minidlna.service
    mv /lib/systemd/system/minidlna.service /lib/systemd/system/minidlnad.service
    systemctl daemon-reload
    systemctl start minidlnad.service
}

configure_x11()
{
    printf " ----- X11 Configuration  ----- \n\n"
    systemctl disable xserver-nodm.service
    systemctl disable getty@tty1
    mv /usr/share/X11/xorg.conf.d/10-evdev.conf /usr/share/X11/xorg.conf.d/45-evdev.conf
}

configure_mediaserver()
{  
    printf " ----- MediaServer Configuration  ----- \n\n"
    echo 'QT_QPA_EVDEV_TOUCHSCREEN_PARAMETERS="/dev/input/event0"' >> /etc/environment
    echo 'QT_QPA_GENERIC_PLUGINS="evdevtouch:/dev/input/event0"' >> /etc/environment
#    echo 'QT_QPA_EGLFS_PHYSICAL_HEIGHT=480' >> /etc/environment
#    echo 'QT_QPA_EGLFS_PHYSICAL_WIDTH=800' >> /etc/environment
    echo 'QT_QPA_EGLFS_DISABLE_INPUT="1"' >> /etc/environment
    mkdir /home/Documents
    mkdir /home/Downloads
    systemctl enable start
}

configure_network()
{
    systemctl enable wpa_supplicant
	systemctl start wpa_supplicant
}

configure_jellyfin()
{
    docker pull jellyfin/jellyfin
	mkdir /etc/Jellyfin/config
	mkdir /etc/Jellyfin/cache
    docker run --volume /etc/Jellyfin/config:/config --volume /etc/Jellyfin/cache:/cache --volume /home:/home_media --volume /mnt:/external_media --net=host --restart=unless-stopped jellyfin/jellyfin
}

configure_other()
{
    chmod -R 777 /usr/htdocs/ampache/config
	systemctl enable psplash
}

set -e

configure_vsftpd
configure_minidlna
configure_x11
configure_mediaserver
configure_other
configure_network
configure_jellyfin

