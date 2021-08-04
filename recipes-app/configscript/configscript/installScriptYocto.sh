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
        systemctl enable docker.service
    fi
}

configure_other()
{	
    systemctl disable serial-getty@ttyS0.service
    systemctl disable getty@tty1
    systemctl enable psplash-start.service
    systemctl enable psplash-quit.service
    systemctl enable mysqld.service
    systemctl disable dhcpcd.service
	echo vm.swappiness=0 | tee -a /etc/sysctl.conf
    pactl set-default-sink 1
}

install_bootstrap()
{
    bootstrapExist=$(ls /opt/youtubedl-web/static/ | grep bootstrap | wc -l)
    if [ $bootstrapExist -gt 0 ]; then
        printf "Boostrap is installed \n"
    else
        cd /opt/youtubedl-web/static
        wget https://github.com/twbs/bootstrap/releases/download/v5.0.0-beta1/bootstrap-5.0.0-beta1-dist.zip
        unzip bootstrap-5.0.0-beta1-dist.zip
        mv bootstrap-5.0.0-beta1-dist bootstrap-5.0.0 --force
        rm bootstrap-5.0.0-beta1-dist.zip
        cd /opt
    fi
}
set -e

install_bootstrap
configure_jellyfin
configure_other
systemctl enable start.service
systemctl disable startup.service
reboot

