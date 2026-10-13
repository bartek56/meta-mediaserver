#!/bin/bash

configure_vim()
{
    printf " ----- VIM configuration  ----- \n"
    mkdir -p /root/.vim
    vimExist=$(ls /root/.vim/ | grep bundle | wc -l)
    if [ $vimExist -gt 0 ]; then
        printf "VIM is configured \n"
    else
        mkdir /root/.vim/bundle
        git clone https://github.com/VundleVim/Vundle.vim.git /root/.vim/bundle/Vundle.vim
    fi
}

configure_serial_gettys()
{
    # if those serial is enable, blutooth not working
    systemctl disable serial-getty@ttyS0.service
    systemctl disable getty@tty1
}

disable_dhcpcd()
{
    systemctl disable dhcpcd.service
}

configure_swappiness()
{
    echo vm.swappiness=0 | tee -a /etc/sysctl.conf
}

configure_volume()
{
    amixer sset "Master" 100%
}

configure_snapweb()
{
    cd /tmp
    wget https://github.com/snapcast/snapweb/releases/download/v0.9.3/snapweb.zip
    rm /usr/share/snapserver/snapweb/index.html
    unzip snapweb.zip -d /usr/share/snapserver/snapweb/
}


