#!/bin/bash

configure_other()
{
    # if those serial is enable, blutooth not working
    systemctl disable serial-getty@ttyS0.service
    systemctl disable getty@tty1
    systemctl enable mysqld.service
    systemctl disable dhcpcd.service
	echo vm.swappiness=0 | tee -a /etc/sysctl.conf

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

set -e

configure_vim
configure_other
reboot
