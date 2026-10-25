#!/bin/sh

set -eu

host_name="$(hostname)"
exec /usr/bin/avahi-publish-service \
    "Snapclient-${host_name}" \
    _snapclient._tcp \
    1704 \
    "host=${host_name}"
