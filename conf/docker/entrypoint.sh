#!/usr/bin/env bash
set -e

export OEROOT=/home/builder/yocto-project/sources/poky
source /home/builder/yocto-project/sources/poky/oe-init-build-env \
    /home/builder/yocto-project/build >/dev/null

if [ "$#" -eq 0 ]; then
    exec bash
fi

exec "$@"
