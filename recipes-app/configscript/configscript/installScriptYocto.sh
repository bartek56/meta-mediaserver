#!/bin/bash

configure_vsftpd()
{
    printf " ----- vsftpd configuration  ----- \n"
    vsftpdExist=$(cat /etc/passwd | grep vsftpd | wc -l)

    if [ $vsftpdExist -gt 0 ]; then
        printf "vsftpd is configured \n"
    else
        adduser -h /home/vsftpd -G nogroup -D -s /bin/false vsftpd
    fi
}

configure_minidlna()
{
    printf " ----- MiniDLNA configuration  ----- \n"
    minidlnadServiceExist=$(ls -l /lib/systemd/system/minidlnad.service | wc -l)
    
    if [ $minidlnadServiceExist -gt 0 ]; then
        printf "MiniDLNA is configured \n"
    else
        systemctl stop minidlna.service
        systemctl disable minidlna.service
        mv /lib/systemd/system/minidlna.service /lib/systemd/system/minidlnad.service
        systemctl daemon-reload
		systemctl enable minidlnad.service
        systemctl start minidlnad.service
    fi
}

configure_x11()
{
    printf " ----- X11 Configuration  ----- \n"
    evdevExist=$(ls -l /usr/share/X11/xorg.conf.d/45-evdev.conf | wc -l)
    if [ $evdevExist -gt 0 ]; then
        printf "X11 is configured \n"
    else
        systemctl disable xserver-nodm.service
        systemctl disable getty@tty1
        mv /usr/share/X11/xorg.conf.d/10-evdev.conf /usr/share/X11/xorg.conf.d/45-evdev.conf
    fi
}

configure_mediaserver()
{ 
    printf " ----- MediaServer Configuration  ----- \n"
    mediaserverIsConfigured=$(cat /etc/environment | grep QT_QPA_EGLFS | wc -l)
    if [ $mediaserverIsConfigured -gt 0 ]; then
        printf "MediaServer is configured \n"
    else
        echo 'QT_QPA_EVDEV_TOUCHSCREEN_PARAMETERS="/dev/input/event0"' >> /etc/environment
        echo 'QT_QPA_GENERIC_PLUGINS="evdevtouch:/dev/input/event0"' >> /etc/environment
#        echo 'QT_QPA_EGLFS_PHYSICAL_HEIGHT=480' >> /etc/environment
#        echo 'QT_QPA_EGLFS_PHYSICAL_WIDTH=800' >> /etc/environment
        echo 'QT_QPA_EGLFS_DISABLE_INPUT="1"' >> /etc/environment
        mkdir /home/Documents
        mkdir /home/Downloads
        systemctl enable start
        passwd
    fi
}

configure_network()
{
    systemctl enable wpa_supplicant
    systemctl start wpa_supplicant
}

configure_jellyfin()
{
    printf " ----- Jellyfin configuration  ----- \n"

    jellyfinContainerExist=$(docker container ls | grep jellyfin | wc -l)
    if [ $jellyfinContainerExist -gt 0 ]; then
    printf "Jellyfin is configured \n"
    else
        i="0"
        test="0"
        while [ $i -lt 30 ]
        do
            test=$(ip address show wlan0 | grep 192 | wc -l)
            if [ $test -gt 0 ]; then
                break
            fi
            echo "waiting for IP address ..."
            sleep 2
            i=$[$i+1]
        done

        if [ $test -gt 0 ]; then
            echo "Connected"
            docker pull jellyfin/jellyfin
            mkdir /etc/Jellyfin
            mkdir /etc/Jellyfin/config
            mkdir /etc/Jellyfin/cache
            docker run -d --volume /etc/Jellyfin/config:/config --volume /etc/Jellyfin/cache:/cache --volume /home:/home_media --volume /mnt:/external_media --net=host --restart=unless-stopped jellyfin/jellyfin
        else
            echo "Network fails"
            echo "You have to manual configure Docker"
        fi
    fi
}

configure_other()
{
    mkdir /usr/lib/systemd/system
	ln -s /lib/systemd/system/alarm.timer /usr/lib/systemd/system/alarm.timer
    ln -s /lib/systemd/system/alarm.service /usr/lib/systemd/system/alarm.service
    ln -s /lib/systemd/system/alarm_snooze.service /usr/lib/systemd/system/alarm_snooze.service
    ln -s /lib/systemd/system/alarm_snooze.timer /usr/lib/systemd/system/alarm_snooze.timer
	chmod -R 777 /usr/htdocs/ampache/config
    systemctl unmask psplash
    systemctl enable psplash
    systemctl disable serial-getty@ttyS0.service
}

set -e

configure_vsftpd
configure_minidlna
configure_x11
configure_mediaserver
configure_other
configure_network
configure_jellyfin

