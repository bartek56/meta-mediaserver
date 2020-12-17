#!/bin/bash


configure_jellyfin()
{
    printf " ----- Jellyfin configuration  ----- \n"

    jellyfinContainerExist=$(docker container ls | grep jellyfin | wc -l)
    if [ $jellyfinContainerExist -gt 0 ]; then
    printf "Jellyfin is configured \n"
    else
        docker pull jellyfin/jellyfin
        mkdir /etc/Jellyfin
        mkdir /etc/Jellyfin/config
        mkdir /etc/Jellyfin/cache
        docker run -d --volume /etc/Jellyfin/config:/config --volume /etc/Jellyfin/cache:/cache --volume /home:/home_media --volume /mnt:/external_media --net=host --restart=unless-stopped jellyfin/jellyfin
    fi
}

configure_other()
{	
    systemctl disable serial-getty@ttyS0.service
    systemctl disable getty@tty1
    systemctl enable psplash-start.service
    systemctl enable psplash-quit.service
	systemctl enable mysqld
}

set -e

configure_jellyfin
configure_other
systemctl enable start.service
systemctl disable startup.service
reboot

