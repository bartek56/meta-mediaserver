SUMMARY = "MediaServer multimedia packages"
DESCRIPTION = "Multimedia services used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    jellyfin \
    snapcast-client \
    snapcast-server \
    snapcast-bt \
    minidlna \
    mpd \
    mpc \
    ympd \
"
