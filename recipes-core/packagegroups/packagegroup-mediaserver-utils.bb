SUMMARY = "MediaServer utility packages"
DESCRIPTION = "System utilities used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    bluez5 \
    i2c-tools \
    bridge-utils \
    hostapd \
    screen \
    certbot \
    at \
    minicom \
    mc \
    curl \
    git \
    bash \
    tzdata \
    nano \
    vim \
"
