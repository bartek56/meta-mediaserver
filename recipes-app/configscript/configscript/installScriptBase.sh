#!/bin/bash


configure_other()
{
    # if those serial is enable, blutooth not working
    systemctl disable serial-getty@ttyS0.service
    systemctl disable getty@tty1
    systemctl enable mysqld.service
    systemctl disable dhcpcd.service
	echo vm.swappiness=0 | tee -a /etc/sysctl.conf

    # access for Apache to enable/disable alarm
    chgrp www-data /etc/mediaserver/alarm.sh
    chgrp www-data /lib/systemd/system/alarm.timer
    chgrp www-data /etc/mediaserver/youtubedl.ini
    chown 775 /etc/mediaserver/youtubedl.ini

    amixer sset "Master" 100%

    # disable HDMI output
    # pactl set-card-profile "alsa_card.platform-bcm2835_audio" off
}

configure_vim()
{
    printf " ----- VIM configuration  ----- \n"
    vimExist=$(ls /home/root/.vim/ | grep bundle | wc -l)
    if [ $vimExist -gt 0 ]; then
        printf "VIM is configured \n"
    else
        mkdir /home/root/.vim/bundle
        git clone https://github.com/VundleVim/Vundle.vim.git /home/root/.vim/bundle/Vundle.vim
    fi
}

install_bootstrap_youtubedl()
{
    printf " ----- Bootstrap for YouTube configuration  ----- \n"
    bootstrapExist=$(ls /opt/youtubedl-web/static/ | grep bootstrap | wc -l)
    if [ $bootstrapExist -gt 0 ]; then
        printf "Boostrap for youtubedl is installed \n"
    else
        cd /opt/youtubedl-web/static
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
configure_vim
configure_other
reboot
