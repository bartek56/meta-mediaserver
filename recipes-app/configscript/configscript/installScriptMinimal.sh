#!/bin/bash

source /opt/installCommon.sh
set -e

configure_vim
configure_snapweb
configure_serial_gettys
disable_dhcpcd
configure_swappiness
configure_volume
