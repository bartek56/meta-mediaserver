#!/bin/bash

source /opt/installCommon.sh
set -e

configure_vim
systemctl enable mysqld.service
disable_dhcpcd
configure_swappiness
configure_volume
