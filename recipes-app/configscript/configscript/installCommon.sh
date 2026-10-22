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


