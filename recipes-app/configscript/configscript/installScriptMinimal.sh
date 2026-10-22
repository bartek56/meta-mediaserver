#!/bin/bash

source /opt/installCommon.sh
set -e

configure_vim
disable_dhcpcd
configure_swappiness
configure_volume
